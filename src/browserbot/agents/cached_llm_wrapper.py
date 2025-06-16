"""
Simple cached LLM wrapper for performance optimization.
"""

import hashlib
import json
from typing import List, Optional, Any, AsyncIterator, Sequence, Union
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.outputs import ChatResult, ChatGeneration, ChatGenerationChunk, LLMResult
from langchain_core.callbacks import CallbackManagerForLLMRun, AsyncCallbackManagerForLLMRun
from langchain_core.runnables import RunnableConfig

from ..core.cache import cache_manager
from ..core.logger import get_logger
from ..core.progress import get_progress_manager, TaskStatus

logger = get_logger(__name__)


class CachedLLMWrapper:
    """
    A simple wrapper that adds caching to any LangChain chat model.
    """
    
    def __init__(self, base_llm: BaseChatModel, cache_ttl: int = 7200):
        """
        Initialize the cached LLM wrapper.
        
        Args:
            base_llm: The underlying LLM to wrap
            cache_ttl: Cache TTL in seconds (default 2 hours)
        """
        self.base_llm = base_llm
        self.cache_ttl = cache_ttl
        self._cache_stats = {"hits": 0, "misses": 0}
        
        # Copy essential attributes from base LLM
        for attr in ['model_name', 'temperature', 'max_tokens', 'streaming']:
            if hasattr(base_llm, attr):
                setattr(self, attr, getattr(base_llm, attr))
    
    def _generate_cache_key(self, messages: List[BaseMessage], **kwargs) -> str:
        """Generate a cache key from messages and parameters."""
        # Create a stable representation of the messages
        message_data = []
        for msg in messages:
            message_data.append({
                "type": msg.__class__.__name__,
                "content": msg.content,
                "additional_kwargs": getattr(msg, 'additional_kwargs', {})
            })
        
        # Include relevant kwargs that affect the output
        cache_data = {
            "messages": message_data,
            "model": getattr(self.base_llm, "model_name", getattr(self.base_llm, "model", None)),
            "temperature": getattr(self.base_llm, "temperature", None),
            "max_tokens": getattr(self.base_llm, "max_tokens", None),
            "tools": str(kwargs.get("tools", [])),
            "tool_choice": str(kwargs.get("tool_choice", None))
        }
        
        # Generate hash
        cache_str = json.dumps(cache_data, sort_keys=True)
        return hashlib.sha256(cache_str.encode()).hexdigest()
    
    async def ainvoke(
        self,
        input: Union[str, List[BaseMessage]],
        config: Optional[RunnableConfig] = None,
        **kwargs: Any
    ) -> BaseMessage:
        """Async invoke with caching."""
        # Convert string to messages if needed
        if isinstance(input, str):
            from langchain_core.messages import HumanMessage
            messages = [HumanMessage(content=input)]
        else:
            messages = input
        
        # Generate cache key
        cache_key = self._generate_cache_key(messages, **kwargs)
        
        # Try to get from cache
        model_name = getattr(self.base_llm, "model_name", getattr(self.base_llm, "model", "unknown"))
        cached_response = await cache_manager.get_cached_ai_response(cache_key, model_name)
        
        progress = get_progress_manager()
        
        if cached_response:
            self._cache_stats["hits"] += 1
            hit_rate = self._cache_stats['hits'] / (self._cache_stats['hits'] + self._cache_stats['misses']) * 100
            
            progress.status(f"Using cached AI response (cache hit rate: {hit_rate:.0f}%)", TaskStatus.INFO)
            logger.debug(
                "Cache hit for AI response",
                hit_rate=f"{hit_rate:.1f}%"
            )
            
            # Return cached message
            try:
                cached_data = json.loads(cached_response)
                return AIMessage(
                    content=cached_data.get("content", ""),
                    additional_kwargs=cached_data.get("additional_kwargs", {})
                )
            except Exception as e:
                logger.warning(f"Failed to deserialize cached response: {e}")
        
        self._cache_stats["misses"] += 1
        
        # Generate new response
        result = await self.base_llm.ainvoke(input, config, **kwargs)
        
        # Cache the response
        try:
            cache_data = {
                "content": result.content,
                "additional_kwargs": getattr(result, "additional_kwargs", {})
            }
            
            await cache_manager.cache_ai_response(
                cache_key,
                json.dumps(cache_data),
                model_name,
                ttl=self.cache_ttl
            )
        except Exception as e:
            logger.warning(f"Failed to cache AI response: {e}")
        
        return result
    
    def invoke(self, *args, **kwargs):
        """Sync invoke delegates to base LLM."""
        return self.base_llm.invoke(*args, **kwargs)
    
    async def agenerate(self, *args, **kwargs):
        """Async generate delegates to base LLM for now."""
        return await self.base_llm.agenerate(*args, **kwargs)
    
    def generate(self, *args, **kwargs):
        """Sync generate delegates to base LLM."""
        return self.base_llm.generate(*args, **kwargs)
    
    async def astream(self, *args, **kwargs):
        """Streaming bypasses cache."""
        async for chunk in self.base_llm.astream(*args, **kwargs):
            yield chunk
    
    def stream(self, *args, **kwargs):
        """Streaming bypasses cache."""
        for chunk in self.base_llm.stream(*args, **kwargs):
            yield chunk
    
    def get_cache_stats(self) -> dict:
        """Get cache statistics."""
        total = self._cache_stats["hits"] + self._cache_stats["misses"]
        hit_rate = (self._cache_stats["hits"] / total * 100) if total > 0 else 0
        
        return {
            "hits": self._cache_stats["hits"],
            "misses": self._cache_stats["misses"],
            "total": total,
            "hit_rate": f"{hit_rate:.1f}%"
        }
    
    # Delegate all other method calls to the base LLM
    def __getattr__(self, name):
        """Delegate attribute access to the base LLM."""
        return getattr(self.base_llm, name)