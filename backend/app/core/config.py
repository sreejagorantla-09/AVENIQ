import os
import logging
from typing import Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

# Resolve absolute path to the root .env file dynamically
# config.py is in backend/app/core/, so the root directory is 3 levels up
current_dir = os.path.dirname(os.path.abspath(__file__))
root_env_path = os.path.abspath(os.path.join(current_dir, "..", "..", "..", ".env"))

class Settings(BaseSettings):
    # App Settings
    ENV: str = "development"
    PROJECT_NAME: str = "AVENIQ"
    API_V1_STR: str = "/api/v1"
    TRUSTED_PROXY: bool = False
    
    # Supabase Settings
    SUPABASE_URL: Optional[str] = None
    SUPABASE_PUBLISHABLE_KEY: Optional[str] = None
    SUPABASE_SECRET_KEY: Optional[str] = None
    
    # Gemini Settings
    GEMINI_API_KEY: Optional[str] = None
    
    # Razorpay Settings
    RAZORPAY_KEY_ID: Optional[str] = None
    RAZORPAY_KEY_SECRET: Optional[str] = None
    RAZORPAY_WEBHOOK_SECRET: Optional[str] = None
    
    @field_validator("SUPABASE_URL", mode="before")
    @classmethod
    def clean_supabase_url(cls, v: Optional[str]) -> Optional[str]:
        if v and isinstance(v, str):
            v = v.strip()
            # Remove trailing slash first
            if v.endswith("/"):
                v = v[:-1]
            # Strip /rest/v1 if appended
            if v.endswith("/rest/v1"):
                v = v[:-8]
            # Strip trailing slash again
            if v.endswith("/"):
                v = v[:-1]
        return v

    model_config = SettingsConfigDict(
        env_file=root_env_path,
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def validate_secrets(self) -> None:
        """
        Validates that all required configuration variables are present in production.
        In development, logs warnings if variables are missing.
        """
        required_vars = [
            ("SUPABASE_URL", self.SUPABASE_URL),
            ("SUPABASE_PUBLISHABLE_KEY", self.SUPABASE_PUBLISHABLE_KEY),
            ("SUPABASE_SECRET_KEY", self.SUPABASE_SECRET_KEY),
            ("GEMINI_API_KEY", self.GEMINI_API_KEY),
            ("RAZORPAY_KEY_ID", self.RAZORPAY_KEY_ID),
            ("RAZORPAY_KEY_SECRET", self.RAZORPAY_KEY_SECRET),
            ("RAZORPAY_WEBHOOK_SECRET", self.RAZORPAY_WEBHOOK_SECRET),
        ]
        
        missing = [name for name, val in required_vars if not val]
        
        if self.ENV == "production":
            if missing:
                raise ValueError(
                    f"Production environment requires the following variables to be set: {', '.join(missing)}"
                )
        else:
            if missing:
                logger.warning(
                    f"Development warning: The following variables are not set: {', '.join(missing)}. "
                    "Ensure these are provided in .env before testing corresponding integrations."
                )

# Initialize settings
settings = Settings()
# Execute secrets check on startup
settings.validate_secrets()
