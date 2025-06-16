"""
Cached LLM wrapper for performance optimization.
"""

import hashlib
import json
from typing import List, Optional, Any, AsyncIterator
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.outputs import ChatResult, ChatGeneration, ChatGenerationChunk
from langchain_core.callbacks import CallbackManagerForLLMRun, AsyncCallbackManagerForLLMRun

from ..core.cache import cache_manager
from ..core.logger import get_logger

logger = get_logger(__name__)


class CachedChatOpenAI(BaseChatModel):
    """
    A wrapper around ChatOpenAI that adds caching capabilities.
    """
    
    def __init__(self, base_llm: BaseChatModel, cache_ttl: int = 7200, **kwargs):
        """
        Initialize the cached LLM wrapper.
        
        Args:
            base_llm: The underlying LLM to wrap
            cache_ttl: Cache TTL in seconds (default 2 hours)
        """
        super().__init__(**kwargs)
        self._base_llm = base_llm
        self._cache_ttl = cache_ttl
        self._cache_stats = {"hits": 0, "misses": 0}
    
    def _generate_cache_key(self, messages: List[BaseMessage], **kwargs) -> str:
        """Generate a cache key from messages and parameters."""
        # Create a stable representation of the messages
        message_data = []
        for msg in messages:
            message_data.append({
                "type": msg.__class__.__name__,
                "content": msg.content,
                "additional_kwargs": msg.additional_kwargs
            })
        
        # Include relevant kwargs that affect the output
        cache_data = {
            "messages": message_data,
            "model": getattr(self._base_llm, "model_name", None),
            "temperature": getattr(self._base_llm, "temperature", None),
            "max_tokens": getattr(self._base_llm, "max_tokens", None),
            "tools": kwargs.get("tools", None),
            "tool_choice": kwargs.get("tool_choice", None)
        }
        
        # Generate hash
        cache_str = json.dumps(cache_data, sort_keys=True)
        return hashlib.sha256(cache_str.encode()).hexdigest()
    
    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs: Any
    ) -> ChatResult:
        """Generate chat response with caching."""
        # Generate cache key
        cache_key = self._generate_cache_key(messages, **kwargs)
        
        # Try to get from cache
        cached_response = await cache_manager.get_cached_ai_response(
            cache_key, 
            getattr(self._base_llm, "model_name", "unknown")
        )
        
        if cached_response:
            self._cache_stats["hits"] += 1
            logger.debug(
                "Cache hit for AI response",
                hit_rate=f"{self._cache_stats['hits'] / (self._cache_stats['hits'] + self._cache_stats['misses']) * 100:.1f}%"
            )
            
            # Deserialize the cached response
            try:
                cached_data = json.loads(cached_response)
                # Reconstruct ChatResult from cached data
                generations = [
                    ChatGeneration(
                        message=BaseMessage.parse_obj(gen["message"]),
                        generation_info=gen.get("generation_info")
                    )
                    for gen in cached_data["generations"]
                ]
                
                return ChatResult(
                    generations=generations,
                    llm_output=cached_data.get("llm_output")
                )
            except Exception as e:
                logger.warning(f"Failed to deserialize cached response: {e}")
                # Fall through to generate new response
        
        self._cache_stats["misses"] += 1
        
        # Generate new response
        result = await self._base_llm._agenerate(
            messages=messages,
            stop=stop,
            run_manager=run_manager,
            **kwargs
        )
        
        # Cache the response
        try:
            # Serialize the result for caching
            cache_data = {
                "generations": [
                    {
                        "message": gen.message.dict(),
                        "generation_info": gen.generation_info
                    }
                    for gen in result.generations
                ],
                "llm_output": result.llm_output
            }
            
            await cache_manager.cache_ai_response(
                cache_key,
                json.dumps(cache_data),
                getattr(self._base_llm, "model_name", "unknown"),
                ttl=self._cache_ttl
            )
        except Exception as e:
            logger.warning(f"Failed to cache AI response: {e}")
        
        return result
    
    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any
    ) -> ChatResult:
        """Synchronous generation (delegates to base LLM)."""
        # For sync calls, just use the base LLM without caching
        return self._base_llm._generate(
            messages=messages,
            stop=stop,
            run_manager=run_manager,
            **kwargs
        )
    
    async def _astream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs: Any
    ) -> AsyncIterator[ChatGenerationChunk]:
        """Stream responses (no caching for streaming)."""
        # Streaming bypasses cache
        async for chunk in self._base_llm._astream(
            messages=messages,
            stop=stop,
            run_manager=run_manager,
            **kwargs
        ):
            yield chunk
    
    @property
    def _llm_type(self) -> str:
        """Return the LLM type."""
        return f"cached_{self._base_llm._llm_type}"
    
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
    
    # Delegate all other attributes to the base LLM
    def __getattr__(self, name):
        """Delegate attribute access to the base LLM."""
        return getattr(self._base_llm, name)