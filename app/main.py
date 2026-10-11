from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse as FastAPIFileResponse

from app.config import settings
from app.database import engine, Base
from app.routers import files, health, samples

# Ensure database tables are created
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "Production-grade Geospatial Measurement API for AEREO Cloud.\n\n"
        "Accepts **Shapefiles (.zip)** and **KML (.kml)** files, extracts features, "
        "dynamically reprojects geographic coordinates (`EPSG:4326`) into metric Universal Transverse Mercator (`UTM`) "
        "planar coordinate reference systems, and calculates high-precision **Area** and **Length** measurements."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(files.router, prefix=settings.API_V1_STR)
app.include_router(health.router, prefix=settings.API_V1_STR)
app.include_router(samples.router, prefix=settings.API_V1_STR)

# Mount Static Files for the Clean Web UI
static_dir = Path(__file__).resolve().parent / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/", include_in_schema=False)
def serve_dashboard():
    """Serves the minimal, professional GIS measurement dashboard."""
    index_file = static_dir / "index.html"
    if index_file.exists():
        return FastAPIFileResponse(str(index_file))
    return {
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": "/docs",
        "api": "/api/files/"
    }
