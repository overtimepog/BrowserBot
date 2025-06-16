"""
Configuration management for BrowserBot.
"""

from typing import Optional, Dict, Any, Union
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, validator


class Settings(BaseSettings):
    """Application settings with validation and type checking."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        protected_namespaces=('settings_',)
    )
    
    # API Keys
    openrouter_api_key: str = Field(..., description="OpenRouter API key")
    openai_api_key: Optional[str] = Field(None, description="OpenAI API key")
    anthropic_api_key: Optional[str] = Field(None, description="Anthropic API key")
    
    # Model Configuration
    model_url: str = Field(
        default="https://openrouter.ai/api/v1",
        description="OpenRouter API base URL"
    )
    model_name: str = Field(
        default="deepseek/deepseek-chat:free",
        description="Default AI model to use"
    )
    model_temperature: float = Field(
        default=0.7,
        description="Model temperature for response generation"
    )
    model_max_tokens: int = Field(
        default=4096,
        description="Maximum tokens for model response"
    )
    
    # Browser Configuration
    browser_headless: bool = Field(
        default=False,
        description="Run browser in headless mode"
    )
    browser_timeout: int = Field(
        default=30000,
        description="Default browser timeout in milliseconds"
    )
    browser_viewport_width: int = Field(
        default=1920,
        description="Browser viewport width"
    )
    browser_viewport_height: int = Field(
        default=1080,
        description="Browser viewport height"
    )
    browser_user_agent: Optional[str] = Field(
        None,
        description="Custom user agent string"
    )
    
    # Docker/Display Configuration
    display: str = Field(
        default=":99",
        description="X11 display number for GUI"
    )
    vnc_port: int = Field(
        default=5900,
        description="VNC server port"
    )
    vnc_password: str = Field(
        default="browserbot",
        description="VNC server password"
    )
    
    # Memory/Storage Configuration
    redis_url: str = Field(
        default="redis://redis:6379/0",
        description="Redis connection URL"
    )
    redis_password: Optional[str] = Field(
        default="browserbot123",
        description="Redis password"
    )
    database_url: str = Field(
        default="sqlite:///./data/browserbot.db",
        description="Database connection URL"
    )
    
    # Logging Configuration
    log_level: str = Field(
        default="INFO",
        description="Logging level"
    )
    log_format: str = Field(
        default="json",
        description="Log format (json or text)"
    )
    log_file: Optional[Path] = Field(
        default=Path("logs/browserbot.log"),
        description="Log file path"
    )
    
    # Security Configuration
    enable_auth: bool = Field(
        default=True,
        description="Enable authentication"
    )
    secret_key: str = Field(
        default="change-me-in-production",
        description="Secret key for encryption"
    )
    allowed_origins: Union[str, list[str]] = Field(
        default=["http://localhost:3000"],
        description="Allowed CORS origins"
    )
    
    # Performance Configuration
    max_concurrent_browsers: int = Field(
        default=8,
        description="Maximum concurrent browser instances"
    )
    min_warm_browsers: int = Field(
        default=2,
        description="Minimum warm browser instances to maintain"
    )
    max_retries: int = Field(
        default=3,
        description="Maximum retry attempts"
    )
    retry_delay: float = Field(
        default=0.5,
        description="Initial retry delay in seconds"
    )
    enable_caching: bool = Field(
        default=True,
        description="Enable caching for performance optimization"
    )
    reduce_delays: bool = Field(
        default=True,
        description="Reduce delays for faster execution"
    )
    
    # Monitoring Configuration
    enable_metrics: bool = Field(
        default=True,
        description="Enable Prometheus metrics"
    )
    metrics_port: int = Field(
        default=8000,
        description="Prometheus metrics port"
    )
    enable_tracing: bool = Field(
        default=True,
        description="Enable OpenTelemetry tracing"
    )
    
    @validator("log_file", pre=True)
    def create_log_directory(cls, v: Optional[Path]) -> Optional[Path]:
        """Ensure log directory exists."""
        if v:
            path = Path(v)
            path.parent.mkdir(parents=True, exist_ok=True)
            return path
        return v
    
    @validator("database_url", pre=True)
    def create_data_directory(cls, v: str) -> str:
        """Ensure data directory exists for SQLite."""
        if v.startswith("sqlite"):
            path = Path(v.replace("sqlite:///", ""))
            path.parent.mkdir(parents=True, exist_ok=True)
        return v
    
    @validator("allowed_origins", pre=True)
    def parse_allowed_origins(cls, v) -> list[str]:
        """Parse comma-separated string into list."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        elif isinstance(v, list):
            return v
        return ["http://localhost:3000"]
    
    def get_model_config(self) -> Dict[str, Any]:
        """Get model configuration for LangChain."""
        config = {
            "model": self.model_name,
            "temperature": self.model_temperature,
            "max_tokens": self.model_max_tokens,
            "api_key": self.openrouter_api_key,
            "base_url": self.model_url,
        }
        
        # Use lower temperature for Mistral models to improve tool calling reliability
        if "mistral" in self.model_name.lower() and "openrouter" in self.model_url.lower():
            config["temperature"] = 0.1
            
        return config
    
    def get_browser_config(self) -> Dict[str, Any]:
        """Get browser configuration for Playwright."""
        config = {
            "headless": self.browser_headless,
            "timeout": self.browser_timeout,
            "viewport": {
                "width": self.browser_viewport_width,
                "height": self.browser_viewport_height,
            }
        }
        if self.browser_user_agent:
            config["user_agent"] = self.browser_user_agent
        return config


# Create global settings instance
settings = Settings()