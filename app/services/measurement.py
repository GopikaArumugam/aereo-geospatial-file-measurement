from typing import Any, Dict, Optional, Tuple
from shapely.geometry.base import BaseGeometry
from shapely.geometry import (
    Polygon, MultiPolygon,
    LineString, MultiLineString,
    Point, MultiPoint,
    GeometryCollection
)
from shapely.validation import make_valid
from pyproj import CRS
from app.services.crs_service import CRSService


class MeasurementResult:
    def __init__(
        self,
        status: str,
        projected_crs_name: Optional[str] = None,
        area_sq_meters: Optional[float] = None,
        area_hectares: Optional[float] = None,
        area_sq_km: Optional[float] = None,
        length_meters: Optional[float] = None,
        length_km: Optional[float] = None,
        notes: Optional[str] = None
    ):
        self.status = status
        self.projected_crs_name = projected_crs_name
        self.area_sq_meters = area_sq_meters
        self.area_hectares = area_hectares
        self.area_sq_km = area_sq_km
        self.length_meters = length_meters
        self.length_km = length_km
        self.notes = notes


class MeasurementService:
    """
    Computes accurate metric measurements (Area, Length) on geometries.
    
    Ensures input geometries are projected from geographic coordinates (EPSG:4326)
    into an optimal metric coordinate reference system (UTM) prior to Euclidean math.
    """

    @classmethod
    def calculate_measurement(
        cls,
        geom: BaseGeometry,
        source_crs: CRS
    ) -> MeasurementResult:
        """
        Calculates metric area or length for a given Shapely geometry.
        
        Supported types:
        - Polygon / MultiPolygon -> Area (m², ha, km²)
        - LineString / MultiLineString -> Length (m, km)
        - Point / MultiPoint -> Skipped (points have 0 area & length)
        - GeometryCollection / Unknown -> Handled gracefully with descriptive notes
        """
        if geom is None or geom.is_empty:
            return MeasurementResult(
                status="EMPTY",
                notes="Geometry is empty or null"
            )

        # Validate and fix topology if needed (e.g. self-intersecting polygons)
        if not geom.is_valid:
            try:
                geom = make_valid(geom)
            except Exception as e:
                return MeasurementResult(
                    status="INVALID",
                    notes=f"Geometry is topologically invalid and could not be repaired: {str(e)}"
                )

        # Handle Points
        if isinstance(geom, (Point, MultiPoint)):
            return MeasurementResult(
                status="SKIPPED",
                notes="Point geometry does not have measurable area or length"
            )

        # Determine optimal projected CRS (UTM) and reproject
        try:
            target_crs, projected_crs_name = CRSService.get_projected_crs_for_geometry(geom, source_crs)
            projected_geom = CRSService.reproject_geometry(geom, source_crs, target_crs)
        except Exception as e:
            return MeasurementResult(
                status="CRS_TRANSFORMATION_ERROR",
                notes=f"Failed to transform geometry to projected CRS: {str(e)}"
            )

        # Calculate for Polygons / MultiPolygons
        if isinstance(projected_geom, (Polygon, MultiPolygon)):
            area_m2 = float(projected_geom.area)
            return MeasurementResult(
                status="CALCULATED",
                projected_crs_name=projected_crs_name,
                area_sq_meters=area_m2,
                area_hectares=area_m2 / 10_000.0,
                area_sq_km=area_m2 / 1_000_000.0,
                notes=None
            )

        # Calculate for LineStrings / MultiLineStrings
        if isinstance(projected_geom, (LineString, MultiLineString)):
            len_m = float(projected_geom.length)
            return MeasurementResult(
                status="CALCULATED",
                projected_crs_name=projected_crs_name,
                length_meters=len_m,
                length_km=len_m / 1_000.0,
                notes=None
            )

        # Handle GeometryCollection
        if isinstance(projected_geom, GeometryCollection):
            total_area = sum(g.area for g in projected_geom.geoms if isinstance(g, (Polygon, MultiPolygon)))
            total_len = sum(g.length for g in projected_geom.geoms if isinstance(g, (LineString, MultiLineString)))
            
            return MeasurementResult(
                status="CALCULATED",
                projected_crs_name=projected_crs_name,
                area_sq_meters=total_area if total_area > 0 else None,
                area_hectares=(total_area / 10_000.0) if total_area > 0 else None,
                area_sq_km=(total_area / 1_000_000.0) if total_area > 0 else None,
                length_meters=total_len if total_len > 0 else None,
                length_km=(total_len / 1_000.0) if total_len > 0 else None,
                notes="Composite GeometryCollection measured across constituent parts"
            )

        # Unsupported geometry
        return MeasurementResult(
            status="UNSUPPORTED",
            projected_crs_name=projected_crs_name,
            notes=f"Geometry type '{geom.geom_type}' is not supported for area or length measurement"
        )
