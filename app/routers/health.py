from fastapi import APIRouter
from app.config import settings
from app.schemas import HealthResponse

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/", response_model=HealthResponse)
def get_health():
    """Service health check and capabilities summary."""
    return HealthResponse(
        status="healthy",
        version=settings.VERSION,
        supported_formats=[".zip (Shapefile)", ".kml (Keyhole Markup Language)"],
        capabilities=[
            "Dynamic EPSG:4326 to UTM CRS reprojection",
            "Polygon & MultiPolygon area calculation (m², ha, km²)",
            "LineString & MultiLineString length calculation (m, km)",
            "Point geometry grace handling",
            "GeoJSON FeatureCollection export"
        ]
    )
