"""Factory for creating agents with feature flags and enhancements."""

from typing import Optional, Dict, Any
from langchain_core.language_models import BaseChatModel
from .browser_agent import BrowserAgent
from .mistral_tool_executor import MistralToolExecutor
from .enhanced_executor import EnhancedToolExecutor
from ..core.feature_flags import is_feature_enabled
from ..core.logger import setup_logger
from ..browser.browser_manager import BrowserManager
from ..browser.advanced_stealth import AdvancedStealth

logger = setup_logger(__name__)

class AgentFactory:
    """Factory for creating browser agents with appropriate enhancements."""
    
    @staticmethod
    async def create_browser_agent(
        task: str,
        model_name: Optional[str] = None,
        headless: bool = False,
        user_id: Optional[str] = None
    ) -> BrowserAgent:
        """Create a browser agent with feature-flag-based enhancements."""
        
        # Initialize browser manager
        browser_manager = BrowserManager()
        await browser_manager.initialize()
        
        # Create base agent
        agent = BrowserAgent(model_name=model_name)
        
        # Apply enhancements based on feature flags
        
        # Enhanced executor
        if is_feature_enabled("enhanced_executor", user_id):
            logger.info("Using enhanced executor with open source improvements")
            agent._use_enhanced_executor = True
        
        # Advanced stealth
        if is_feature_enabled("advanced_stealth", user_id):
            logger.info("Applying advanced stealth techniques")
            agent._stealth_handler = AdvancedStealth()
        
        # Vision fallback
        if is_feature_enabled("vision_fallback", user_id):
            logger.info("Enabling computer vision fallback")
            agent._enable_vision = True
        
        # Multi-agent coordination
        if is_feature_enabled("multi_agent", user_id):
            logger.info("Enabling multi-agent coordination")
            agent._multi_agent_mode = True
        
        # Performance monitoring
        if is_feature_enabled("performance_monitoring", user_id):
            logger.info("Enabling detailed performance monitoring")
            agent._enable_monitoring = True
        
        return agent

    @staticmethod
    def create_tool_executor(
        tools: Dict[str, Any],
        llm: BaseChatModel,
        model_name: str,
        user_id: Optional[str] = None
    ):
        """Create appropriate tool executor based on model and feature flags."""
        
        # Check if we should use enhanced executor
        if is_feature_enabled("enhanced_executor", user_id):
            logger.info("Creating enhanced tool executor")
            executor = EnhancedToolExecutor(tools, llm)
            
            # Configure based on feature flags
            executor.fallback_to_playwright = is_feature_enabled("natural_language_fallback", user_id)
            executor.enable_vision = is_feature_enabled("vision_fallback", user_id)
            executor.stealth_mode = is_feature_enabled("human_typing", user_id)
            
            return executor
        
        # Check if model needs custom executor (Mistral)
        elif "mistral" in model_name.lower():
            logger.info("Creating Mistral tool executor")
            return MistralToolExecutor(tools, llm)
        
        # Default to standard executor
        else:
            logger.info("Using standard LangChain executor")
            return None  # Use LangChain's default

    @staticmethod
    def get_agent_config(user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get agent configuration based on feature flags."""
        return {
            "enhanced_executor": is_feature_enabled("enhanced_executor", user_id),
            "advanced_stealth": is_feature_enabled("advanced_stealth", user_id),
            "vision_fallback": is_feature_enabled("vision_fallback", user_id),
            "multi_agent": is_feature_enabled("multi_agent", user_id),
            "smart_retry": is_feature_enabled("smart_retry", user_id),
            "human_typing": is_feature_enabled("human_typing", user_id),
            "browser_pooling": is_feature_enabled("browser_pooling", user_id),
            "natural_language_fallback": is_feature_enabled("natural_language_fallback", user_id),
            "performance_monitoring": is_feature_enabled("performance_monitoring", user_id),
            "adaptive_delays": is_feature_enabled("adaptive_delays", user_id)
        }

    @staticmethod
    async def create_experiment_agent(
        experiment_name: str,
        user_id: str,
        task: str,
        model_name: Optional[str] = None
    ) -> BrowserAgent:
        """Create an agent for A/B testing experiments."""
        from ..core.feature_flags import get_feature_flags
        
        flags = get_feature_flags()
        variant = flags.get_experiment_variant(experiment_name, user_id)
        
        logger.info(f"User {user_id} assigned to variant {variant} in experiment {experiment_name}")
        
        # Create agent with variant-specific configuration
        agent = await AgentFactory.create_browser_agent(
            task=task,
            model_name=model_name,
            user_id=user_id
        )
        
        # Apply variant-specific settings
        if variant:
            agent._experiment_variant = variant
            agent._experiment_name = experiment_name
        
        return agent