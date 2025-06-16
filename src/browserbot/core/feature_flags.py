"""Feature flags system for gradual rollout and A/B testing."""

import os
import json
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from ..core.cache import get_cache_client
from ..core.logger import setup_logger

logger = setup_logger(__name__)

class FeatureFlags:
    """Feature flag management with Redis backend and fallback defaults."""
    
    def __init__(self):
        self.cache = get_cache_client()
        self.prefix = "feature_flag:"
        self.ttl = 300  # 5 minutes cache
        
        # Default feature flags
        self.defaults = {
            "enhanced_executor": {
                "enabled": True,
                "description": "Use enhanced tool executor with open source improvements",
                "rollout_percentage": 100
            },
            "advanced_stealth": {
                "enabled": True,
                "description": "Use advanced stealth techniques from 2024 research",
                "rollout_percentage": 100
            },
            "vision_fallback": {
                "enabled": False,
                "description": "Enable computer vision fallback when selectors fail",
                "rollout_percentage": 0
            },
            "multi_agent": {
                "enabled": False,
                "description": "Enable multi-agent coordination for complex tasks",
                "rollout_percentage": 0
            },
            "smart_retry": {
                "enabled": True,
                "description": "Use intelligent retry strategies with exponential backoff",
                "rollout_percentage": 100
            },
            "human_typing": {
                "enabled": True,
                "description": "Type with human-like delays and occasional corrections",
                "rollout_percentage": 100
            },
            "browser_pooling": {
                "enabled": True,
                "description": "Use browser instance pooling for performance",
                "rollout_percentage": 100
            },
            "natural_language_fallback": {
                "enabled": True,
                "description": "Parse natural language when JSON parsing fails",
                "rollout_percentage": 100
            },
            "performance_monitoring": {
                "enabled": True,
                "description": "Enable detailed performance monitoring and metrics",
                "rollout_percentage": 100
            },
            "adaptive_delays": {
                "enabled": True,
                "description": "Adapt delays based on site behavior and load times",
                "rollout_percentage": 100
            }
        }
        
        # Initialize flags in cache if not present
        self._initialize_flags()

    def _initialize_flags(self) -> None:
        """Initialize default flags in cache if they don't exist."""
        try:
            for flag_name, flag_config in self.defaults.items():
                key = f"{self.prefix}{flag_name}"
                if not self.cache.get(key):
                    self.cache.set(key, flag_config, ttl=None)  # No expiry for defaults
                    logger.info(f"Initialized feature flag: {flag_name}")
        except Exception as e:
            logger.warning(f"Could not initialize flags in cache: {e}")

    def is_enabled(self, flag_name: str, user_id: Optional[str] = None) -> bool:
        """Check if a feature flag is enabled."""
        try:
            # Try to get from cache first
            key = f"{self.prefix}{flag_name}"
            flag_data = self.cache.get(key)
            
            if not flag_data:
                # Fallback to defaults
                flag_data = self.defaults.get(flag_name, {"enabled": False})
            
            # Check if globally enabled
            if not flag_data.get("enabled", False):
                return False
            
            # Check rollout percentage
            rollout = flag_data.get("rollout_percentage", 100)
            if rollout < 100:
                # Use user_id for consistent rollout
                if user_id:
                    # Simple hash-based rollout
                    user_hash = hash(user_id) % 100
                    return user_hash < rollout
                else:
                    # Random rollout for anonymous users
                    import random
                    return random.randint(0, 99) < rollout
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking feature flag {flag_name}: {e}")
            # Safe default: return False for unknown flags
            return self.defaults.get(flag_name, {}).get("enabled", False)

    def get_all_flags(self) -> Dict[str, Any]:
        """Get all feature flags and their current status."""
        all_flags = {}
        
        # Get from defaults first
        for flag_name in self.defaults:
            all_flags[flag_name] = self.get_flag(flag_name)
        
        # Try to get any additional flags from cache
        try:
            pattern = f"{self.prefix}*"
            for key in self.cache.client.scan_iter(match=pattern):
                flag_name = key.decode().replace(self.prefix, "")
                if flag_name not in all_flags:
                    all_flags[flag_name] = self.cache.get(key)
        except Exception as e:
            logger.warning(f"Could not scan cache for flags: {e}")
        
        return all_flags

    def get_flag(self, flag_name: str) -> Dict[str, Any]:
        """Get full flag configuration."""
        try:
            key = f"{self.prefix}{flag_name}"
            flag_data = self.cache.get(key)
            
            if not flag_data:
                flag_data = self.defaults.get(flag_name, {
                    "enabled": False,
                    "description": "Unknown flag",
                    "rollout_percentage": 0
                })
            
            return flag_data
        except Exception as e:
            logger.error(f"Error getting flag {flag_name}: {e}")
            return self.defaults.get(flag_name, {
                "enabled": False,
                "description": "Unknown flag",
                "rollout_percentage": 0
            })

    def set_flag(self, flag_name: str, enabled: bool, 
                 rollout_percentage: Optional[int] = None,
                 description: Optional[str] = None) -> bool:
        """Set or update a feature flag."""
        try:
            key = f"{self.prefix}{flag_name}"
            
            # Get existing flag or create new
            flag_data = self.get_flag(flag_name)
            
            # Update values
            flag_data["enabled"] = enabled
            if rollout_percentage is not None:
                flag_data["rollout_percentage"] = max(0, min(100, rollout_percentage))
            if description is not None:
                flag_data["description"] = description
            
            # Add metadata
            flag_data["last_updated"] = datetime.utcnow().isoformat()
            flag_data["updated_by"] = "system"
            
            # Save to cache
            self.cache.set(key, flag_data, ttl=None)
            logger.info(f"Updated feature flag {flag_name}: enabled={enabled}")
            
            return True
        except Exception as e:
            logger.error(f"Error setting flag {flag_name}: {e}")
            return False

    def delete_flag(self, flag_name: str) -> bool:
        """Delete a feature flag (reverts to default if exists)."""
        try:
            key = f"{self.prefix}{flag_name}"
            self.cache.client.delete(key)
            logger.info(f"Deleted feature flag: {flag_name}")
            return True
        except Exception as e:
            logger.error(f"Error deleting flag {flag_name}: {e}")
            return False

    def create_experiment(self, experiment_name: str, 
                         variants: Dict[str, Dict[str, Any]],
                         traffic_split: Dict[str, int]) -> bool:
        """Create an A/B testing experiment."""
        try:
            experiment_key = f"experiment:{experiment_name}"
            experiment_data = {
                "name": experiment_name,
                "variants": variants,
                "traffic_split": traffic_split,
                "created_at": datetime.utcnow().isoformat(),
                "status": "active"
            }
            
            self.cache.set(experiment_key, experiment_data, ttl=None)
            logger.info(f"Created experiment: {experiment_name}")
            return True
        except Exception as e:
            logger.error(f"Error creating experiment {experiment_name}: {e}")
            return False

    def get_experiment_variant(self, experiment_name: str, 
                              user_id: Optional[str] = None) -> Optional[str]:
        """Get the variant for a user in an experiment."""
        try:
            experiment_key = f"experiment:{experiment_name}"
            experiment_data = self.cache.get(experiment_key)
            
            if not experiment_data or experiment_data.get("status") != "active":
                return None
            
            traffic_split = experiment_data.get("traffic_split", {})
            
            # Use user_id for consistent assignment
            if user_id:
                user_hash = hash(f"{experiment_name}:{user_id}") % 100
            else:
                import random
                user_hash = random.randint(0, 99)
            
            # Assign to variant based on traffic split
            cumulative = 0
            for variant, percentage in traffic_split.items():
                cumulative += percentage
                if user_hash < cumulative:
                    return variant
            
            return None
        except Exception as e:
            logger.error(f"Error getting experiment variant: {e}")
            return None


# Global feature flags instance
_feature_flags = None

def get_feature_flags() -> FeatureFlags:
    """Get the global feature flags instance."""
    global _feature_flags
    if _feature_flags is None:
        _feature_flags = FeatureFlags()
    return _feature_flags

def is_feature_enabled(flag_name: str, user_id: Optional[str] = None) -> bool:
    """Convenience function to check if a feature is enabled."""
    return get_feature_flags().is_enabled(flag_name, user_id)