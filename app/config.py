import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Detect serverless environments (Vercel, AWS Lambda)
IS_SERVERLESS = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))


class Settings(BaseSettings):
    PROJECT_NAME: str = "AEREO Geospatial File Measurement API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    
    # Base Directory
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    
    # Storage settings: on serverless platforms, only /tmp is writable
    UPLOAD_DIR: Path = Path("/tmp/uploads") if IS_SERVERLESS else (BASE_DIR / "uploads")
    
    # Database: on serverless platforms, use /tmp/geospatial.db
    DATABASE_URL: str = "sqlite:////tmp/geospatial.db" if IS_SERVERLESS else "sqlite:///./geospatial.db"
    
    # Constraints
    MAX_FILE_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: set = {".zip", ".kml"}
    
    # CRS defaults
    DEFAULT_GEOGRAPHIC_CRS: str = "EPSG:4326"

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="allow"
    )


settings = Settings()

# Ensure uploads directory exists safely
try:
    settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    pass
