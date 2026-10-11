from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from app.config import settings

router = APIRouter(prefix="/samples", tags=["Samples"])

SAMPLES_DIR = settings.BASE_DIR / "sample_data"


@router.get("/mining-pit.kml")
def get_sample_kml():
    """Returns sample mining pit KML file for quick demonstration."""
    sample_path = SAMPLES_DIR / "sample_mining_pit.kml"
    if not sample_path.exists():
        raise HTTPException(status_code=404, detail="Sample KML file not found")
    return FileResponse(
        str(sample_path),
        media_type="application/vnd.google-earth.kml+xml",
        filename="sample_mining_pit.kml"
    )


@router.get("/corridor-survey.zip")
def get_sample_shapefile_zip():
    """Returns sample infrastructure corridor zipped Shapefile for quick demonstration."""
    sample_path = SAMPLES_DIR / "sample_corridor_survey.zip"
    if not sample_path.exists():
        raise HTTPException(status_code=404, detail="Sample Shapefile zip not found")
    return FileResponse(
        str(sample_path),
        media_type="application/zip",
        filename="sample_corridor_survey.zip"
    )
