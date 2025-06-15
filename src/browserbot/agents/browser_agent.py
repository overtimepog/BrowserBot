"""
Main browser agent that combines AI reasoning with browser automation capabilities.
"""

import asyncio
from typing import Dict, Any, List, Optional, AsyncIterator
from datetime import datetime
import json

from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, trim_messages
from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory
from pydantic import BaseModel, Field

from ..browser.browser_manager import BrowserManager
from ..browser.page_controller import PageController
from ..browser.stealth import StealthConfig
from ..core.config import settings
from ..core.logger import get_logger
from ..core.errors import BrowserError, AIModelError, ConfigurationError
from ..core.retry import with_retry

from .tools import create_browser_tools
from .prompts import BrowserAgentPrompts

logger = get_logger(__name__)


class InMemoryHistory(BaseChatMessageHistory, BaseModel):
    """In-memory implementation of chat message history with automatic trimming."""
    
    messages: List[BaseMessage] = Field(default_factory=list)
    max_message_pairs: int = Field(default=10)
    
    def add_messages(self, messages: List[BaseMessage]) -> None:
        """Add messages and automatically trim to window size."""
        self.messages.extend(messages)
        
        # Keep only the last max_message_pairs * 2 messages
        max_messages = self.max_message_pairs * 2
        if len(self.messages) > max_messages:
            # Ensure we start with a human message
            trim_point = len(self.messages) - max_messages
            while trim_point < len(self.messages) and isinstance(self.messages[trim_point], AIMessage):
                trim_point += 1
            self.messages = self.messages[trim_point:]
    
    def clear(self) -> None:
        """Clear all messages."""
        self.messages = []


class BrowserAgent:
    """
    Intelligent browser automation agent powered by AI.
    
    This agent combines large language models with browser automation
    to perform complex web tasks through natural language instructions.
    """
    
    def __init__(
        self,
        model_name: Optional[str] = None,
        max_browsers: int = None,
        stealth_config: Optional[StealthConfig] = None,
        memory_size: int = 10
    ):
        self.model_name = model_name or settings.model_name
        self.browser_manager = BrowserManager(
            max_browsers=max_browsers,
            stealth_config=stealth_config
        )
        
        # Memory configuration
        self.memory_size = memory_size
        self.chat_histories: Dict[str, InMemoryHistory] = {}
        
        # Initialize LLM
        self.llm = self._create_llm()
        
        # Agent components (initialized when first used)
        self.agent_executor: Optional[AgentExecutor] = None
        self.current_page_controller: Optional[PageController] = None
        self.session_id: str = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Create message trimmer for consistent window behavior
        self.message_trimmer = trim_messages(
            max_tokens=self.memory_size * 2,  # Convert pairs to message count
            strategy="last",
            token_counter=len,  # Count messages instead of tokens
            include_system=True,
            allow_partial=False,
            start_on="human"
        )
        
        logger.info(
            "Browser agent initialized",
            model_name=self.model_name,
            session_id=self.session_id
        )
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.browser_manager.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.shutdown()
    
    def _create_llm(self) -> ChatOpenAI:
        """Create and configure the language model."""
        try:
            model_config = settings.get_model_config()
            
            # Add OpenRouter headers if using OpenRouter
            default_headers = {}
            if "openrouter" in model_config.get("base_url", "").lower():
                default_headers = {
                    "HTTP-Referer": "https://github.com/BrowserBot",
                    "X-Title": "BrowserBot"
                }
            
            return ChatOpenAI(
                model=model_config["model"],
                temperature=model_config["temperature"],
                max_tokens=model_config["max_tokens"],
                openai_api_key=model_config["api_key"],
                openai_api_base=model_config["base_url"],
                streaming=True,
                default_headers=default_headers
            )
            
        except Exception as e:
            logger.error("Failed to create LLM", error=str(e))
            raise ConfigurationError(f"Failed to create language model: {e}")
    
    def _get_session_history(self, session_id: str) -> BaseChatMessageHistory:
        """Get or create chat history for a session."""
        if session_id not in self.chat_histories:
            self.chat_histories[session_id] = InMemoryHistory(max_message_pairs=self.memory_size)
        return self.chat_histories[session_id]
    
    async def execute_task(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        max_iterations: int = 15
    ) -> Dict[str, Any]:
        """
        Execute a high-level task using AI reasoning and browser automation.
        
        Args:
            task: Natural language description of the task
            context: Additional context for the task
            max_iterations: Maximum number of agent iterations
            
        Returns:
            Dictionary containing task results and execution details
        """
        logger.info(f"Starting task execution: {task}")
        
        try:
            # Ensure browser manager is initialized
            if not self.browser_manager._initialized:
                await self.browser_manager.initialize()
            
            # Get a browser context for this task
            async with self.browser_manager.get_browser() as browser_context:
                page = await browser_context.new_page()
                self.current_page_controller = PageController(page)
                
                # Create agent executor with current browser context
                agent_executor = await self._create_agent_executor()
                
                # Execute the task
                result = await self._execute_with_agent(
                    agent_executor,
                    task,
                    context,
                    max_iterations
                )
                
                # Add execution metadata
                result.update({
                    "session_id": self.session_id,
                    "execution_time": datetime.now().isoformat(),
                    "browser_stats": self.browser_manager.get_stats()
                })
                
                logger.info("Task execution completed", task=task, success=result.get("success"))
                return result
                
        except Exception as e:
            logger.error("Task execution failed", task=task, error=str(e))
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "task": task,
                "session_id": self.session_id
            }
    
    async def chat(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Have a conversational interaction with the agent.
        
        Args:
            message: User message
            context: Additional context
            
        Returns:
            Agent response and any actions taken
        """
        logger.info(f"Processing chat message: {message[:100]}...")
        
        try:
            # Ensure we have an active browser session
            if not self.current_page_controller:
                async with self.browser_manager.get_browser() as browser_context:
                    page = await browser_context.new_page()
                    self.current_page_controller = PageController(page)
            
            # Create or get agent executor
            if not self.agent_executor:
                self.agent_executor = await self._create_agent_executor()
            
            # Process the message
            response = await self.agent_executor.ainvoke(
                {"input": message}
            )
            
            # Add messages to history
            history = self._get_session_history(self.session_id)
            history.add_messages([
                HumanMessage(content=message),
                AIMessage(content=response["output"])
            ])
            
            return {
                "success": True,
                "response": response["output"],
                "intermediate_steps": response.get("intermediate_steps", []),
                "session_id": self.session_id
            }
            
        except Exception as e:
            logger.error("Chat processing failed", message=message[:100], error=str(e))
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "message": message,
                "session_id": self.session_id
            }
    
    async def stream_task(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncIterator[Dict[str, Any]]:
        """
        Execute a task with streaming responses.
        
        Args:
            task: Task description
            context: Additional context
            
        Yields:
            Streaming updates about task execution
        """
        logger.info(f"Starting streaming task: {task}")
        
        yield {"type": "start", "task": task, "session_id": self.session_id}
        
        try:
            # Ensure browser manager is initialized
            if not self.browser_manager._initialized:
                await self.browser_manager.initialize()
                yield {"type": "status", "message": "Browser manager initialized"}
            
            async with self.browser_manager.get_browser() as browser_context:
                page = await browser_context.new_page()
                self.current_page_controller = PageController(page)
                
                yield {"type": "status", "message": "Browser session created"}
                
                # Create agent executor
                agent_executor = await self._create_agent_executor()
                yield {"type": "status", "message": "AI agent initialized"}
                
                # Execute with streaming
                async for update in self._stream_agent_execution(
                    agent_executor,
                    task,
                    context
                ):
                    yield update
                
                yield {"type": "complete", "session_id": self.session_id}
                
        except Exception as e:
            logger.error("Streaming task failed", task=task, error=str(e))
            yield {
                "type": "error",
                "error": str(e),
                "error_type": type(e).__name__,
                "session_id": self.session_id
            }
    
    async def _create_agent_executor(self) -> AgentExecutor:
        """Create an agent executor with intelligent model-specific handling."""
        if not self.current_page_controller:
            raise ConfigurationError("No active page controller")
        
        # Create browser automation tools
        tools = create_browser_tools(self.current_page_controller)
        
        # Get the base prompt and create agent
        prompt = BrowserAgentPrompts.get_system_prompt()
        
        # Intelligent model detection and handling
        model_lower = self.model_name.lower()
        
        # Models with strong native tool calling support
        if any(model in model_lower for model in ["deepseek", "qwen", "gpt-", "claude", "gemini"]):
            logger.info("Using native tool calling agent", model=self.model_name)
            
            # Use create_tool_calling_agent for models with excellent tool calling
            agent = create_tool_calling_agent(self.llm, tools, prompt)
            
            agent_executor = AgentExecutor(
                agent=agent,
                tools=tools,
                verbose=True,
                return_intermediate_steps=True,
                max_iterations=15,
                handle_parsing_errors=True
            )
            
            return agent_executor
            
        elif "mistral" in model_lower:
            logger.info("Using custom Mistral tool executor", model=self.model_name)
            
            # For Mistral models, use custom agent with manual tool execution
            from .mistral_tool_executor import MistralToolExecutor
            tool_executor = MistralToolExecutor(tools, self.llm)
            return tool_executor
            
        else:
            logger.info("Using fallback tool calling agent", model=self.model_name)
            
            # Default fallback for unknown models
            try:
                agent = create_tool_calling_agent(self.llm, tools, prompt)
                
                agent_executor = AgentExecutor(
                    agent=agent,
                    tools=tools,
                    verbose=True,
                    return_intermediate_steps=True,
                    max_iterations=15,
                    handle_parsing_errors=True
                )
                
                return agent_executor
                
            except Exception as e:
                logger.warning("Standard tool calling failed, using Mistral fallback", error=str(e))
                
                # Ultimate fallback to custom parser
                from .mistral_tool_executor import MistralToolExecutor
                tool_executor = MistralToolExecutor(tools, self.llm)
                return tool_executor
    
    @with_retry(max_attempts=2, exceptions=(AIModelError,))
    async def _execute_with_agent(
        self,
        agent_executor: AgentExecutor,
        task: str,
        context: Optional[Dict[str, Any]],
        max_iterations: int
    ) -> Dict[str, Any]:
        """Execute task with the agent executor."""
        try:
            # Prepare input
            input_data = {
                "input": task
            }
            
            if context:
                input_data["context"] = json.dumps(context, indent=2)
            
            logger.debug(f"Executing agent with input: {input_data}")
            logger.debug(f"Using model: {self.model_name}")
            
            # Execute without session configuration since we're not using RunnableWithMessageHistory
            result = await agent_executor.ainvoke(input_data)
            
            logger.debug(f"Agent execution result: {result}")
            
            return {
                "success": True,
                "output": result["output"],
                "intermediate_steps": result.get("intermediate_steps", []),
                "iterations": len(result.get("intermediate_steps", [])),
                "action_history": self.current_page_controller.get_action_history() if self.current_page_controller else []
            }
            
        except Exception as e:
            logger.error(f"Agent execution error: {type(e).__name__}: {str(e)}", exc_info=True)
            
            if "rate limit" in str(e).lower() or "quota" in str(e).lower():
                raise AIModelError(f"API rate limit or quota exceeded: {e}")
            elif "timeout" in str(e).lower():
                raise AIModelError(f"API timeout: {e}")
            else:
                raise AIModelError(f"Agent execution failed: {e}")
    
    async def _stream_agent_execution(
        self,
        agent_executor: AgentExecutor,
        task: str,
        context: Optional[Dict[str, Any]]
    ) -> AsyncIterator[Dict[str, Any]]:
        """Stream agent execution with intermediate results."""
        try:
            # This is a simplified streaming implementation
            # In a full implementation, you'd want to integrate with LangChain's streaming callbacks
            
            input_data = {
                "input": task
            }
            if context:
                input_data["context"] = json.dumps(context, indent=2)
            
            # Execute and yield intermediate steps
            result = await agent_executor.ainvoke(input_data)
            
            # Yield intermediate steps
            for i, (action, observation) in enumerate(result.get("intermediate_steps", [])):
                yield {
                    "type": "step",
                    "step": i + 1,
                    "action": str(action),
                    "observation": str(observation)
                }
            
            # Yield final result
            yield {
                "type": "result",
                "output": result["output"],
                "total_steps": len(result.get("intermediate_steps", []))
            }
            
        except Exception as e:
            yield {
                "type": "error",
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    async def get_current_page_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the current page."""
        if self.current_page_controller:
            return await self.current_page_controller.get_page_info()
        return None
    
    async def take_screenshot(self, full_page: bool = False) -> Optional[bytes]:
        """Take a screenshot of the current page."""
        if self.current_page_controller:
            return await self.current_page_controller.take_screenshot(full_page=full_page)
        return None
    
    def get_conversation_history(self) -> List[BaseMessage]:
        """Get the conversation history for the current session."""
        history = self._get_session_history(self.session_id)
        return history.messages
    
    def clear_conversation_history(self) -> None:
        """Clear the conversation history for the current session."""
        history = self._get_session_history(self.session_id)
        history.clear()
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get session statistics."""
        history = self._get_session_history(self.session_id)
        return {
            "session_id": self.session_id,
            "model_name": self.model_name,
            "conversation_length": len(history.messages),
            "browser_stats": self.browser_manager.get_stats(),
            "action_history": (
                self.current_page_controller.get_action_history()
                if self.current_page_controller else []
            )
        }
    
    async def shutdown(self) -> None:
        """Shutdown the agent and cleanup resources."""
        logger.info("Shutting down browser agent", session_id=self.session_id)
        
        try:
            await self.browser_manager.shutdown()
            logger.info("Browser agent shutdown complete")
        except Exception as e:
            logger.error("Error during agent shutdown", error=str(e))