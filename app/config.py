from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "AEREO Geospatial File Measurement API"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api"
    
    # Storage settings
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    
    # Database
    DATABASE_URL: str = "sqlite:///./geospatial.db"
    
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

# Ensure uploads directory exists
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
