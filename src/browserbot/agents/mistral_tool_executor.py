"""
Custom tool executor for Mistral models that don't support native function calling.

This module provides a fallback implementation that parses Mistral's JSON responses
and converts them to actual tool executions, working around limitations in 
OpenRouter's Mistral tool calling support.
"""

import json
import re
import asyncio
from typing import Dict, Any, List, Optional, AsyncIterator
from datetime import datetime

from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.runnables import Runnable
from langchain.tools import BaseTool

from .mistral_parser import MistralToolParser
from .prompts import BrowserAgentPrompts
from ..core.logger import get_logger
from ..core.errors import AIModelError, BrowserError

logger = get_logger(__name__)


class MistralToolExecutor:
    """
    Custom tool executor for Mistral models with JSON-based tool calling.
    
    Since Mistral models on OpenRouter don't support native function calling,
    this executor parses JSON tool calls from the model's text output and
    executes them manually.
    """
    
    def __init__(self, tools: List[BaseTool], llm):
        """
        Initialize the Mistral tool executor.
        
        Args:
            tools: List of available browser automation tools
            llm: The language model instance
        """
        self.tools = {tool.name: tool for tool in tools}
        self.llm = llm
        self.parser = MistralToolParser()
        
        logger.info(
            "Initialized Mistral tool executor",
            tool_count=len(self.tools),
            tool_names=[tool.name for tool in tools]
        )
    
    async def ainvoke(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the Mistral agent with custom tool parsing.
        
        Args:
            input_data: Input containing the user request
            
        Returns:
            Dictionary with execution results and intermediate steps
        """
        try:
            task = input_data.get("input", "")
            logger.info("Starting Mistral tool execution", task=task[:100])
            
            # Get the enhanced prompt for Mistral
            prompt = self._get_mistral_prompt()
            
            # Format the prompt with available tools
            formatted_prompt = prompt.format(
                tools=self._format_tools_for_prompt(),
                task=task
            )
            
            # Track execution steps
            intermediate_steps = []
            max_iterations = 15
            iteration = 0
            
            # Main execution loop
            current_context = formatted_prompt
            
            while iteration < max_iterations:
                iteration += 1
                logger.debug(f"Mistral execution iteration {iteration}")
                
                # Get response from LLM
                response = await self._get_llm_response(current_context)
                
                # Check if this is a final answer
                if self._is_final_answer(response):
                    logger.info("Mistral provided final answer", iteration=iteration)
                    return {
                        "success": True,
                        "output": response,
                        "intermediate_steps": intermediate_steps,
                        "iterations": iteration
                    }
                
                # Parse tool calls from response
                tool_calls = self._extract_tool_calls(response)
                
                if not tool_calls:
                    # No tool calls found, log the response for debugging
                    logger.warning(
                        "No tool calls found in response",
                        response_preview=response[:200],
                        response_length=len(response)
                    )
                    # Check if this looks like it should have been parsed
                    if any(pattern in response for pattern in ['"name":', '"tool":', '"arguments":']):
                        logger.error(
                            "Response appears to contain tool calls but parsing failed",
                            response_preview=response[:500]
                        )
                        # Log the full response for debugging
                        logger.debug("Full response that failed to parse", response=response)
                    
                    # Treat as final answer
                    logger.info("Treating response as final answer since no tool calls were parsed")
                    return {
                        "success": True,
                        "output": response,
                        "intermediate_steps": intermediate_steps,
                        "iterations": iteration
                    }
                
                # Execute tool calls
                for tool_call in tool_calls:
                    tool_name = tool_call.get("name") or tool_call.get("tool")
                    tool_args = tool_call.get("arguments", {})
                    
                    if tool_name not in self.tools:
                        error_msg = f"Unknown tool: {tool_name}"
                        logger.warning(error_msg)
                        intermediate_steps.append((tool_call, f"Error: {error_msg}"))
                        continue
                    
                    # Execute the tool
                    try:
                        logger.debug(f"Executing tool: {tool_name}", args=tool_args)
                        tool_result = await self.tools[tool_name]._arun(tool_args)
                        intermediate_steps.append((tool_call, tool_result))
                        
                        # Update context with tool result
                        current_context += f"\n\nTool {tool_name} executed with result: {tool_result}\n\nContinue with the task or provide the final answer:"
                        
                    except Exception as e:
                        error_msg = f"Tool execution failed: {str(e)}"
                        logger.error(error_msg, tool=tool_name, error=str(e))
                        intermediate_steps.append((tool_call, f"Error: {error_msg}"))
                        current_context += f"\n\nTool {tool_name} failed with error: {error_msg}\n\nTry a different approach or provide the final answer:"
            
            # Max iterations reached
            logger.warning("Max iterations reached", iterations=max_iterations)
            return {
                "success": False,
                "output": "Maximum iterations reached without completion",
                "intermediate_steps": intermediate_steps,
                "iterations": iteration,
                "error": "Max iterations exceeded"
            }
            
        except Exception as e:
            logger.error("Mistral tool execution failed", error=str(e), exc_info=True)
            return {
                "success": False,
                "output": f"Tool execution failed: {str(e)}",
                "intermediate_steps": [],
                "iterations": 0,
                "error": str(e)
            }
    
    async def _get_llm_response(self, prompt: str) -> str:
        """Get response from the language model."""
        try:
            messages = [HumanMessage(content=prompt)]
            response = await self.llm.ainvoke(messages)
            return response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            logger.error("LLM invocation failed", error=str(e))
            raise AIModelError(f"Failed to get LLM response: {e}")
    
    def _extract_tool_calls(self, response: str) -> List[Dict[str, Any]]:
        """
        Extract tool calls from Mistral's text response.
        
        Supports multiple formats:
        1. JSON code blocks: ```json {...} ``` (handles multiple JSON objects)
        2. Multiple JSON objects in sequence
        3. Direct JSON: { "name": "tool", "arguments": {...} }
        4. Function-like calls: tool_name({"param": "value"})
        """
        tool_calls = []
        
        # Debug: log the raw response to understand format
        logger.debug(f"Extracting tool calls from response: {repr(response[:500])}")
        
        # Pattern 1: Check for raw JSON objects first (no code blocks)
        if response.strip().startswith('{') and not response.strip().startswith('```'):
            logger.debug("Detected raw JSON format without code blocks")
            
            # Method 1: Try to parse the entire response as multiple JSON objects
            # Look for complete JSON objects by tracking braces
            current_depth = 0
            current_obj = []
            in_string = False
            escape_next = False
            
            for char in response:
                if escape_next:
                    escape_next = False
                    current_obj.append(char)
                    continue
                    
                if char == '\\' and in_string:
                    escape_next = True
                    current_obj.append(char)
                    continue
                    
                if char == '"' and not escape_next:
                    in_string = not in_string
                    
                if not in_string:
                    if char == '{':
                        current_depth += 1
                    elif char == '}':
                        current_depth -= 1
                
                current_obj.append(char)
                
                # When we complete a JSON object
                if current_depth == 0 and current_obj and char == '}':
                    json_str = ''.join(current_obj).strip()
                    if json_str:
                        logger.debug(f"Attempting to parse extracted JSON: {repr(json_str[:100])}")
                        try:
                            parsed = json.loads(json_str)
                            if "name" in parsed:
                                args = self._normalize_tool_arguments(parsed["name"], parsed.get("arguments", {}))
                                tool_calls.append({
                                    "name": parsed["name"],
                                    "arguments": args
                                })
                                logger.debug(f"Successfully parsed raw tool call: {parsed['name']}")
                            elif "tool" in parsed:
                                args = self._normalize_tool_arguments(parsed["tool"], parsed.get("arguments", {}))
                                tool_calls.append({
                                    "name": parsed["tool"],
                                    "arguments": args
                                })
                                logger.debug(f"Successfully parsed raw tool call: {parsed['tool']}")
                        except json.JSONDecodeError as e:
                            logger.warning(
                                "Failed to parse JSON tool call",
                                json_text=json_str[:200],
                                error=str(e)
                            )
                    current_obj = []
            
            # If we found tool calls this way, return them
            if tool_calls:
                logger.info(f"Extracted {len(tool_calls)} tool calls using brace tracking")
                return tool_calls
            
            # Method 2: Fallback to splitting by newlines (single or double)
            # Split by any newline pattern and filter out empty strings
            json_objects = [obj.strip() for obj in re.split(r'\n+', response) if obj.strip() and obj.strip().startswith('{')]
            
            for j, json_obj in enumerate(json_objects):
                logger.debug(f"Attempting to parse split JSON object {j}: {repr(json_obj[:100])}")
                try:
                    parsed = json.loads(json_obj)
                    if "name" in parsed:
                        args = self._normalize_tool_arguments(parsed["name"], parsed.get("arguments", {}))
                        tool_calls.append({
                            "name": parsed["name"],
                            "arguments": args
                        })
                        logger.debug(f"Successfully parsed raw tool call: {parsed['name']}")
                    elif "tool" in parsed:
                        args = self._normalize_tool_arguments(parsed["tool"], parsed.get("arguments", {}))
                        tool_calls.append({
                            "name": parsed["tool"],
                            "arguments": args
                        })
                        logger.debug(f"Successfully parsed raw tool call: {parsed['tool']}")
                except json.JSONDecodeError as e:
                    logger.debug(f"Failed to parse split JSON object {j}: {json_obj[:100]}", error=str(e))
                    continue
        
        # Pattern 2: JSON in markdown code blocks (enhanced to handle multiple objects)
        if not tool_calls:
            json_block_pattern = r'```json\s*(.*?)\s*```'
            block_matches = re.findall(json_block_pattern, response, re.DOTALL)
            
            logger.debug(f"Found {len(block_matches)} JSON code blocks")
            
            for i, block in enumerate(block_matches):
                # Handle multiple JSON objects separated by newlines or empty lines
                block = block.strip()
                logger.debug(f"Processing block {i}: {repr(block[:200])}")
                
                # Method 1: Split by double newlines to get individual JSON objects
                json_objects = [obj.strip() for obj in block.split('\n\n') if obj.strip()]
                logger.debug(f"Split into {len(json_objects)} JSON objects")
                
                for j, json_obj in enumerate(json_objects):
                    logger.debug(f"Attempting to parse object {j}: {repr(json_obj[:100])}")
                    try:
                        parsed = json.loads(json_obj)
                        if "name" in parsed:
                            args = self._normalize_tool_arguments(parsed["name"], parsed.get("arguments", {}))
                            tool_calls.append({
                                "name": parsed["name"],
                                "arguments": args
                            })
                            logger.debug(f"Successfully parsed tool call: {parsed['name']}")
                        elif "tool" in parsed:
                            args = self._normalize_tool_arguments(parsed["tool"], parsed.get("arguments", {}))
                            tool_calls.append({
                                "name": parsed["tool"],
                                "arguments": args
                            })
                            logger.debug(f"Successfully parsed tool call: {parsed['tool']}")
                    except json.JSONDecodeError as e:
                        logger.debug(f"Failed to parse JSON object {j}: {json_obj[:100]}", error=str(e))
                        continue
            
            # Method 2: If we still haven't found anything, try regex pattern matching on each block
            if not tool_calls and block_matches:
                for block in block_matches:
                    # Find individual JSON objects using regex
                    json_obj_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
                    json_objects = re.findall(json_obj_pattern, block)
                    
                    for obj_str in json_objects:
                        if '"name"' in obj_str or '"tool"' in obj_str:
                            try:
                                parsed = json.loads(obj_str)
                                if "name" in parsed:
                                    args = self._normalize_tool_arguments(parsed["name"], parsed.get("arguments", {}))
                                    tool_calls.append({
                                        "name": parsed["name"],
                                        "arguments": args
                                    })
                                elif "tool" in parsed:
                                    args = self._normalize_tool_arguments(parsed["tool"], parsed.get("arguments", {}))
                                    tool_calls.append({
                                        "name": parsed["tool"],
                                        "arguments": args
                                    })
                            except json.JSONDecodeError:
                                continue
        
        # Pattern 3: Multiple JSON objects outside code blocks
        if not tool_calls:
            # Look for curly braces and try to extract JSON objects
            brace_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
            potential_objects = re.findall(brace_pattern, response)
            
            for obj_str in potential_objects:
                if '"name"' in obj_str or '"tool"' in obj_str:
                    try:
                        parsed = json.loads(obj_str)
                        if "name" in parsed:
                            args = self._normalize_tool_arguments(parsed["name"], parsed.get("arguments", {}))
                            tool_calls.append({
                                "name": parsed["name"],
                                "arguments": args
                            })
                        elif "tool" in parsed:
                            args = self._normalize_tool_arguments(parsed["tool"], parsed.get("arguments", {}))
                            tool_calls.append({
                                "name": parsed["tool"],
                                "arguments": args
                            })
                    except json.JSONDecodeError:
                        continue
        
        # Pattern 4: Function-like calls (fallback)
        if not tool_calls:
            func_pattern = r'(\w+)\s*\(\s*\{([^}]+)\}\s*\)'
            matches = re.findall(func_pattern, response)
            
            for tool_name, args_str in matches:
                tool_mapping = {
                    'navigate': 'navigate',
                    'click': 'interact',
                    'type': 'interact',
                    'extract': 'extract',
                    'wait': 'wait',
                    'screenshot': 'screenshot'
                }
                
                actual_tool = tool_mapping.get(tool_name, tool_name)
                
                if actual_tool in self.tools:
                    try:
                        args = {}
                        for pair in args_str.split(','):
                            if ':' in pair:
                                key, value = pair.split(':', 1)
                                key = key.strip().strip('"\'')
                                value = value.strip().strip('"\'')
                                args[key] = value
                        
                        if actual_tool == 'interact' and 'action' not in args:
                            if tool_name == 'click':
                                args['action'] = 'click'
                            elif tool_name == 'type':
                                args['action'] = 'type'
                        
                        tool_calls.append({
                            "name": actual_tool,
                            "arguments": args
                        })
                    except Exception as e:
                        logger.warning("Failed to parse function-style tool call", error=str(e))
        
        logger.debug(f"Extracted {len(tool_calls)} tool calls", tool_calls=tool_calls)
        return tool_calls
    
    def _normalize_tool_arguments(self, tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize tool arguments to match expected parameter names.
        
        The model sometimes uses different parameter names than what our tools expect.
        """
        normalized = args.copy()
        
        if tool_name == "interact":
            # Map common parameter variations
            if "element" in normalized:
                normalized["selector"] = normalized.pop("element")
            if "value" in normalized and "text" not in normalized:
                normalized["text"] = normalized.pop("value")
            
            # Ensure action is set for interact tool
            if "action" not in normalized:
                if "text" in normalized:
                    normalized["action"] = "type"
                else:
                    normalized["action"] = "click"
        
        elif tool_name == "wait":
            # Map wait parameters
            if "condition" in normalized:
                condition = normalized.pop("condition")
                if condition == "element_exists":
                    normalized["wait_type"] = "element"
                    normalized["state"] = "visible"
                elif condition == "page_load":
                    normalized["wait_type"] = "page_load"
                else:
                    normalized["wait_type"] = "time"
            
            if "element" in normalized:
                normalized["selector"] = normalized.pop("element")
                if "wait_type" not in normalized:
                    normalized["wait_type"] = "element"
            
            if "seconds" in normalized:
                # Convert seconds to milliseconds
                seconds = normalized.pop("seconds")
                normalized["timeout"] = int(seconds) * 1000
                if "wait_type" not in normalized:
                    normalized["wait_type"] = "time"
            
            # Ensure wait_type is always set
            if "wait_type" not in normalized:
                normalized["wait_type"] = "page_load"
        
        elif tool_name == "extract":
            # Map extract parameters
            if "element" in normalized:
                normalized["selector"] = normalized.pop("element")
            if "attribute" not in normalized:
                normalized["extract_type"] = "text"
            else:
                if normalized["attribute"] == "textContent":
                    normalized["extract_type"] = "text"
                    normalized.pop("attribute", None)
                else:
                    normalized["extract_type"] = "attribute"
            
            # Ensure extract_type is set
            if "extract_type" not in normalized:
                normalized["extract_type"] = "text"
        
        return normalized
    
    def _is_final_answer(self, response: str) -> bool:
        """Check if the response represents a final answer."""
        final_indicators = [
            "final answer:",
            "task completed",
            "successfully completed",
            "the price is",
            "the cost is",
            "i found",
            "the search shows",
            "the result is",
            "extracted price:",
            "here's the information"
        ]
        
        response_lower = response.lower()
        return any(indicator in response_lower for indicator in final_indicators)
    
    def _get_mistral_prompt(self) -> str:
        """Get enhanced prompt for Mistral models."""
        return """You are BrowserBot, an AI agent that controls web browsers to complete tasks. You have access to these tools:

{tools}

IMPORTANT INSTRUCTIONS:
1. When you need to use a tool, respond with JSON in this EXACT format:
```json
{{
  "name": "tool_name",
  "arguments": {{
    "param": "value"
  }}
}}
```

2. Execute tools step by step to complete the task
3. After each tool execution, wait for the result before proceeding
4. When you have the final answer, provide a clear summary

Task: {task}

Start by analyzing what needs to be done and execute the first tool."""
    
    def _format_tools_for_prompt(self) -> str:
        """Format available tools for the prompt."""
        tool_descriptions = []
        
        for tool_name, tool in self.tools.items():
            description = getattr(tool, 'description', f"Tool: {tool_name}")
            tool_descriptions.append(f"- {tool_name}: {description}")
        
        return "\n".join(tool_descriptions)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get executor statistics."""
        return {
            "executor_type": "mistral_custom",
            "tool_count": len(self.tools),
            "tools": list(self.tools.keys())
        }