from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class LogConfig(BaseSettings):
    """Configuration settings for structlog_config package."""
    
    json_logger: Optional[bool] = None
    log_level: str = "INFO"
    path_prettify: bool = True
    python_log_path: Optional[str] = None
    no_color: bool = False
    
    # Configure how settings are loaded - use envvar prefix
    model_config = SettingsConfigDict(
        env_prefix="STRUCTLOG_",  # Use STRUCTLOG_* environment variables
        case_sensitive=False,     # Case-insensitive env vars
    )


# Create a singleton instance
config = LogConfig()