"""
Custom output parser for Mistral models to handle tool calling issues.
"""

import re
import json
from typing import Dict, Any, Optional, Union
from langchain_core.exceptions import OutputParserException
from langchain_core.output_parsers import BaseOutputParser
from langchain_core.agents import AgentAction, AgentFinish
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration
from ..core.logger import get_logger

logger = get_logger(__name__)


class MistralToolParser(BaseOutputParser):
    """
    Custom parser to handle Mistral model outputs that may generate code
    instead of properly using tools.
    """
    
    def parse(self, text: Union[str, AIMessage]) -> Union[AgentAction, AgentFinish]:
        """Parse Mistral output and convert to proper tool calls."""
        
        # Handle AIMessage input
        if isinstance(text, AIMessage):
            # Check if the message has tool_calls
            if hasattr(text, 'tool_calls') and text.tool_calls:
                tool_call = text.tool_calls[0]
                return AgentAction(
                    tool=tool_call["name"],
                    tool_input=tool_call["args"],
                    log=str(text)
                )
            
            # Check for function_call (older format)
            if hasattr(text, 'additional_kwargs') and text.additional_kwargs.get('function_call'):
                function_call = text.additional_kwargs['function_call']
                return AgentAction(
                    tool=function_call["name"],
                    tool_input=json.loads(function_call["arguments"]),
                    log=str(text)
                )
            
            # Fall back to text content
            text = text.content
        
        # Now handle string text
        if isinstance(text, str):
            # Check for JSON-like tool calls in the text
            json_pattern = r'\{[^{}]*"tool"[^{}]*:[^{}]*"([^"]+)"[^{}]*\}'
            json_match = re.search(json_pattern, text, re.DOTALL)
            
            if json_match:
                try:
                    # Extract the JSON object
                    json_str = json_match.group(0)
                    tool_data = json.loads(json_str)
                    
                    tool_name = tool_data.get("tool")
                    arguments = tool_data.get("arguments", {})
                    
                    logger.info(f"Parsed tool call from JSON: {tool_name} with args {arguments}")
                    
                    return AgentAction(
                        tool=tool_name,
                        tool_input=arguments,
                        log=text
                    )
                except json.JSONDecodeError:
                    logger.warning("Failed to parse JSON tool call from text")
            
            # Check for code-like patterns that indicate tool usage
            # Pattern: toolName({ param: value })
            code_pattern = r'(\w+)\s*\(\s*\{([^}]+)\}\s*\)'
            code_match = re.search(code_pattern, text)
            
            if code_match:
                tool_name = code_match.group(1)
                params_str = code_match.group(2)
                
                # Map common function names to actual tool names
                tool_mapping = {
                    'navigateTo': 'navigate',
                    'goTo': 'navigate',
                    'click': 'interact',
                    'clickElement': 'interact',
                    'typeText': 'interact',
                    'type': 'interact',
                    'extract': 'extract',
                    'getData': 'extract',
                    'takeScreenshot': 'screenshot',
                    'screenshot': 'screenshot',
                    'waitFor': 'wait',
                    'wait': 'wait'
                }
                
                actual_tool = tool_mapping.get(tool_name, tool_name)
                
                # Parse parameters
                try:
                    # Convert JavaScript-like object notation to Python dict
                    params_str = params_str.strip()
                    params = {}
                    
                    # Simple parameter parsing
                    param_pattern = r'(\w+)\s*:\s*["\']([^"\']+)["\']'
                    for match in re.finditer(param_pattern, params_str):
                        key = match.group(1)
                        value = match.group(2)
                        params[key] = value
                    
                    # Map common parameter names
                    param_mapping = {
                        'url': 'url',
                        'href': 'url',
                        'link': 'url',
                        'element': 'selector',
                        'target': 'selector',
                        'css': 'selector',
                        'xpath': 'selector',
                        'content': 'text',
                        'value': 'text',
                        'input': 'text'
                    }
                    
                    mapped_params = {}
                    for key, value in params.items():
                        mapped_key = param_mapping.get(key, key)
                        mapped_params[mapped_key] = value
                    
                    # Add action type for interact tool
                    if actual_tool == 'interact':
                        if tool_name in ['click', 'clickElement']:
                            mapped_params['action'] = 'click'
                        elif tool_name in ['type', 'typeText']:
                            mapped_params['action'] = 'type'
                    
                    logger.info(f"Parsed tool call from code pattern: {actual_tool} with args {mapped_params}")
                    
                    return AgentAction(
                        tool=actual_tool,
                        tool_input=mapped_params,
                        log=text
                    )
                    
                except Exception as e:
                    logger.warning(f"Failed to parse code-like tool call: {e}")
            
            # Check if this looks like a final answer
            final_answer_patterns = [
                r"Final Answer:",
                r"I have successfully",
                r"Task completed",
                r"Done\.",
                r"The .* has been",
                r"I've .* successfully"
            ]
            
            for pattern in final_answer_patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return AgentFinish(
                        return_values={"output": text},
                        log=text
                    )
            
            # If we can't parse it as a tool call, check if it's describing an action
            action_patterns = [
                (r"navigat\w* to (.+)", "navigate", lambda m: {"url": m.group(1).strip()}),
                (r"go to (.+)", "navigate", lambda m: {"url": m.group(1).strip()}),
                (r"click\w* (?:on |the )?(.+)", "interact", lambda m: {"action": "click", "selector": m.group(1).strip()}),
                (r"type\w* ['\"](.+?)['\"] (?:in|into) (.+)", "interact", lambda m: {"action": "type", "text": m.group(1), "selector": m.group(2).strip()}),
                (r"extract\w* (?:data|text|content) from (.+)", "extract", lambda m: {"selector": m.group(1).strip()}),
            ]
            
            for pattern, tool, param_func in action_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    params = param_func(match)
                    logger.info(f"Inferred tool call from description: {tool} with args {params}")
                    
                    return AgentAction(
                        tool=tool,
                        tool_input=params,
                        log=text
                    )
            
            # Check if it shows JSON in markdown code blocks
            markdown_json = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
            if markdown_json:
                json_content = markdown_json.group(1).strip()
                logger.info(f"Found JSON in markdown block: {repr(json_content[:200])}")
                
                # Try to parse multiple JSON objects separated by newlines
                json_objects = []
                
                # Split by double newlines to get individual JSON objects
                potential_objects = [obj.strip() for obj in json_content.split('\n\n') if obj.strip()]
                
                for obj_str in potential_objects:
                    if obj_str.startswith('{') and obj_str.endswith('}'):
                        try:
                            tool_data = json.loads(obj_str)
                            if "name" in tool_data and "arguments" in tool_data:
                                json_objects.append(tool_data)
                                logger.info(f"Successfully parsed JSON object: {tool_data['name']}")
                        except json.JSONDecodeError:
                            logger.debug(f"Failed to parse JSON object: {obj_str[:100]}")
                            continue
                
                # Return the first tool call found (for now)
                if json_objects:
                    first_tool = json_objects[0]
                    logger.info(f"Using first tool call: {first_tool['name']} (found {len(json_objects)} total)")
                    return AgentAction(
                        tool=first_tool["name"],
                        tool_input=first_tool["arguments"],
                        log=text
                    )
        
        # If nothing matches, raise an error
        raise OutputParserException(
            f"Could not parse tool usage from Mistral output: {text[:200]}..."
        )
    
    def get_format_instructions(self) -> str:
        """Return instructions on how to format output."""
        return """When you need to use a tool, respond with a JSON object in this exact format:
{
    "tool": "tool_name",
    "arguments": {
        "param1": "value1",
        "param2": "value2"
    }
}

Example tool calls:
- Navigate: {"tool": "navigate", "arguments": {"url": "https://example.com"}}
- Click: {"tool": "interact", "arguments": {"action": "click", "selector": "button.submit"}}
- Type: {"tool": "interact", "arguments": {"action": "type", "selector": "#input", "text": "Hello"}}
- Extract: {"tool": "extract", "arguments": {"selector": ".content"}}

Do not write JavaScript code or describe actions. Only output the JSON tool call."""
    
    @property
    def _type(self) -> str:
        """Return the parser type."""
        return "mistral_tool_parser"