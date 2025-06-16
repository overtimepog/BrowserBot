"""Enhanced tool executor with improvements from open source agents."""

import json
import re
from typing import Dict, List, Any, Optional, Tuple
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from ..core.logger import setup_logger

logger = setup_logger(__name__)

class EnhancedToolExecutor:
    """Enhanced tool executor with best practices from Browser-Use, HyperAgent, and Skyvern."""
    
    def __init__(self, tools: Dict[str, Any], llm: BaseChatModel):
        self.tools = tools
        self.llm = llm
        self.max_iterations = 15
        self.fallback_to_playwright = True  # From HyperAgent
        self.enable_vision = True  # From Skyvern
        self.stealth_mode = True  # From HyperAgent
        
    def create_enhanced_prompt(self, task: str) -> str:
        """Create an enhanced prompt with best practices from open source agents."""
        
        tool_descriptions = []
        for name, tool in self.tools.items():
            tool_descriptions.append(f"- {name}: {tool.description}")
        
        return f"""You are an advanced browser automation agent with enhanced capabilities.

TASK: {task}

AVAILABLE TOOLS:
{chr(10).join(tool_descriptions)}

ENHANCED CAPABILITIES:
1. Vision-Based Element Detection: When traditional selectors fail, describe what you're looking for and I'll use computer vision.
2. Anti-Detection Mode: All browser actions are performed with human-like patterns to avoid detection.
3. Smart Fallbacks: If AI-based selection fails, fallback to standard Playwright selectors.
4. Multi-Strategy Approach: Try multiple approaches if the first one fails.

BEST PRACTICES FROM LEADING AGENTS:
- Browser-Use: Always wait for page stability before interacting with elements
- HyperAgent: Use stealth mode and randomized delays between actions
- Skyvern: Leverage visual understanding when DOM-based approaches fail
- AutoGen: Break complex tasks into smaller, verifiable steps

EXECUTION STRATEGY:
1. Analyze the task and plan your approach
2. Use the most appropriate tool for each step
3. Verify results after each action
4. Adapt strategy if something doesn't work
5. Provide clear feedback about what you're doing

IMPORTANT RULES:
- Never hallucinate data - only report what you actually extract
- Use extract_type="text_all" for multiple items
- Always wait for elements to be stable before interacting
- Take screenshots when debugging issues
- Try alternative selectors if the first one fails

For tool calls, use this exact format:
```json
{
  "name": "tool_name",
  "arguments": {
    "param1": "value1",
    "param2": "value2"
  }
}
```

Begin by analyzing the task and executing the necessary tools."""

    def _add_human_like_delays(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Add human-like delays between actions (from HyperAgent)."""
        import random
        
        if tool_name in ['interact', 'navigate']:
            delay = random.uniform(0.5, 2.0)
            return {
                "name": "wait",
                "arguments": {
                    "seconds": delay,
                    "reason": "Human-like delay"
                }
            }
        return None

    def _extract_tool_calls(self, response: str) -> List[Dict[str, Any]]:
        """Extract tool calls with multiple parsing strategies."""
        tool_calls = []
        
        # Strategy 1: JSON blocks (standard)
        json_pattern = r'```json\s*(.*?)\s*```'
        json_matches = re.findall(json_pattern, response, re.DOTALL)
        
        for match in json_matches:
            try:
                tool_call = json.loads(match.strip())
                if isinstance(tool_call, dict) and 'name' in tool_call:
                    tool_calls.append(tool_call)
            except json.JSONDecodeError:
                continue
        
        # Strategy 2: Inline JSON objects (fallback)
        if not tool_calls:
            inline_pattern = r'\{[^{}]*"name"[^{}]*\}'
            inline_matches = re.findall(inline_pattern, response)
            
            for match in inline_matches:
                try:
                    tool_call = json.loads(match)
                    if 'name' in tool_call:
                        tool_calls.append(tool_call)
                except json.JSONDecodeError:
                    continue
        
        # Strategy 3: Natural language fallback (from Skyvern)
        if not tool_calls and self.fallback_to_playwright:
            tool_calls = self._parse_natural_language(response)
        
        return tool_calls

    def _parse_natural_language(self, response: str) -> List[Dict[str, Any]]:
        """Parse natural language instructions into tool calls (from Skyvern)."""
        tool_calls = []
        
        # Common patterns
        patterns = {
            'navigate': r'(?:go to|navigate to|open|visit)\s+(\S+)',
            'click': r'(?:click on|click|press)\s+(?:the\s+)?(.+?)(?:\s+button|\s+link)?',
            'type': r'(?:type|enter|input)\s+"([^"]+)"(?:\s+in(?:to)?\s+(.+?))?',
            'extract': r'(?:extract|get|find|scrape)\s+(?:the\s+)?(.+?)(?:\s+from)?',
        }
        
        response_lower = response.lower()
        
        for tool_name, pattern in patterns.items():
            matches = re.finditer(pattern, response_lower, re.IGNORECASE)
            for match in matches:
                if tool_name == 'navigate':
                    tool_calls.append({
                        "name": "navigate",
                        "arguments": {"url": match.group(1)}
                    })
                elif tool_name == 'click':
                    tool_calls.append({
                        "name": "interact",
                        "arguments": {
                            "selector": match.group(1),
                            "action": "click"
                        }
                    })
                # Add more patterns as needed
        
        return tool_calls

    def _should_use_vision(self, error_message: str) -> bool:
        """Determine if we should fall back to vision-based approach (from Skyvern)."""
        vision_triggers = [
            "element not found",
            "timeout waiting for selector",
            "no element matching selector",
            "element not visible",
            "element not interactable"
        ]
        
        return any(trigger in error_message.lower() for trigger in vision_triggers)

    def _create_vision_task(self, original_task: Dict[str, Any], context: str) -> Dict[str, Any]:
        """Create a vision-based task when selectors fail (from Skyvern)."""
        return {
            "name": "screenshot",
            "arguments": {
                "full_page": True,
                "reason": f"Vision-based fallback for: {context}"
            }
        }

    async def execute(self, task: str, context: Optional[str] = None) -> Dict[str, Any]:
        """Execute task with enhanced strategies from open source agents."""
        messages = []
        
        # Add context if provided (from AutoGen multi-agent pattern)
        if context:
            messages.append(SystemMessage(content=f"Context from previous steps: {context}"))
        
        messages.append(HumanMessage(content=self.create_enhanced_prompt(task)))
        
        for iteration in range(self.max_iterations):
            try:
                # Get AI response
                response = await self.llm.ainvoke(messages)
                response_text = response.content
                
                logger.info(f"Iteration {iteration + 1}: AI response received")
                
                # Extract tool calls
                tool_calls = self._extract_tool_calls(response_text)
                
                if not tool_calls:
                    # No more tools to execute
                    return {
                        "success": True,
                        "result": response_text,
                        "iterations": iteration + 1
                    }
                
                # Execute tools with enhancements
                for tool_call in tool_calls:
                    tool_name = tool_call.get("name")
                    
                    if tool_name not in self.tools:
                        logger.warning(f"Unknown tool: {tool_name}")
                        continue
                    
                    # Add human-like delays if enabled (from HyperAgent)
                    if self.stealth_mode:
                        delay_call = self._add_human_like_delays(tool_name)
                        if delay_call and "wait" in self.tools:
                            await self._execute_single_tool(delay_call)
                    
                    # Execute the actual tool
                    result = await self._execute_single_tool(tool_call)
                    
                    # Check if we should use vision fallback (from Skyvern)
                    if not result.get("success") and self.enable_vision:
                        error_msg = result.get("error", "")
                        if self._should_use_vision(error_msg):
                            vision_task = self._create_vision_task(tool_call, error_msg)
                            vision_result = await self._execute_single_tool(vision_task)
                            # Add vision result to context for next iteration
                            messages.append(HumanMessage(
                                content=f"Vision fallback triggered. Screenshot taken. "
                                       f"Please analyze the screenshot and try a different approach."
                            ))
                    
                    # Add result to conversation
                    messages.append(HumanMessage(
                        content=f"Tool {tool_name} result: {json.dumps(result)}"
                    ))
                
            except Exception as e:
                logger.error(f"Error in iteration {iteration + 1}: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "iterations": iteration + 1
                }
        
        return {
            "success": False,
            "error": "Max iterations reached",
            "iterations": self.max_iterations
        }

    async def _execute_single_tool(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single tool with error handling."""
        tool_name = tool_call.get("name")
        arguments = tool_call.get("arguments", {})
        
        try:
            tool = self.tools[tool_name]
            result = await tool.execute(arguments)
            return result
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return {
                "success": False,
                "error": str(e),
                "tool": tool_name
            }

    async def ainvoke(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """LangChain-compatible async invoke method."""
        task = input_data.get("input", "")
        context = input_data.get("context")
        
        result = await self.execute(task, context)
        
        # Format response for LangChain compatibility
        return {
            "output": result.get("result", result.get("error", "Task execution failed")),
            "intermediate_steps": result.get("tool_calls", []),
            "success": result.get("success", False)
        }
    
    def create_multi_agent_task(self, main_task: str, subtasks: List[str]) -> List[Dict[str, Any]]:
        """Create a multi-agent task structure (from AutoGen patterns)."""
        return [
            {
                "agent": "coordinator",
                "task": main_task,
                "subtasks": subtasks
            },
            {
                "agent": "browser",
                "capabilities": ["navigate", "interact", "extract", "screenshot"]
            },
            {
                "agent": "analyzer", 
                "capabilities": ["vision", "nlp", "data_processing"]
            }
        ]