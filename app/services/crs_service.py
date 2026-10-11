import math
from typing import Optional, Tuple
import pyproj
from pyproj import CRS, Transformer
from shapely.geometry.base import BaseGeometry
from shapely.ops import transform


class CRSService:
    """
    Handles coordinate reference system detection, validation, and transformations.
    
    Prevents erroneous metric calculations on angular geographic coordinates (e.g., EPSG:4326),
    automatically projecting geometries into optimal local metric systems (UTM).
    """

    @staticmethod
    def parse_crs(crs_input: Optional[str]) -> CRS:
        """
        Parses a CRS string, EPSG code, or WKT definition into a pyproj.CRS object.
        Defaults to EPSG:4326 (WGS84) if input is empty or invalid.
        """
        if not crs_input or str(crs_input).strip() == "":
            return CRS.from_epsg(4326)
        
        try:
            return CRS.from_user_input(crs_input)
        except Exception:
            # Fallback to standard WGS84 if unrecognized
            return CRS.from_epsg(4326)

    @staticmethod
    def get_utm_epsg_for_latlon(lat: float, lon: float) -> int:
        """
        Calculates the appropriate EPSG code for the Universal Transverse Mercator (UTM) zone
        given a latitude and longitude in degrees.
        
        UTM divides the Earth into 60 zones, each 6 degrees of longitude wide.
        EPSG 32601-32660: Northern Hemisphere
        EPSG 32701-32760: Southern Hemisphere
        """
        # Normalize longitude to [-180, 180]
        lon = ((lon + 180) % 360) - 180
        # Clamp latitude to [-80, 84] standard UTM limits
        lat = max(-80.0, min(84.0, lat))

        zone_number = int((lon + 180) / 6.0) + 1
        zone_number = max(1, min(60, zone_number))

        if lat >= 0:
            return 32600 + zone_number
        else:
            return 32700 + zone_number

    @classmethod
    def get_projected_crs_for_geometry(
        cls,
        geom: BaseGeometry,
        source_crs: CRS
    ) -> Tuple[CRS, str]:
        """
        Determines the optimal projected coordinate system for a given geometry.
        
        - If the source CRS is already projected (units are linear/meters), returns the source CRS.
        - If the source CRS is geographic (units are degrees), calculates the geometry centroid
          and dynamically resolves the appropriate local UTM zone.
        """
        if source_crs.is_projected:
            # Already in a metric/planar projection
            name = source_crs.to_string()
            return source_crs, name

        # Calculate centroid in geographic space
        centroid = geom.centroid
        lon, lat = centroid.x, centroid.y

        # Determine UTM zone
        utm_epsg = cls.get_utm_epsg_for_latlon(lat, lon)
        projected_crs = CRS.from_epsg(utm_epsg)
        projected_name = f"EPSG:{utm_epsg} (UTM Zone {utm_epsg % 100}{'N' if utm_epsg < 32700 else 'S'})"

        return projected_crs, projected_name

    @classmethod
    def reproject_geometry(
        cls,
        geom: BaseGeometry,
        source_crs: CRS,
        target_crs: CRS
    ) -> BaseGeometry:
        """
        Transforms a Shapely geometry from source_crs to target_crs.
        Enforces always_xy=True to guarantee (x, y) / (lon, lat) axis order consistency.
        """
        if source_crs.equals(target_crs):
            return geom

        transformer = Transformer.from_crs(source_crs, target_crs, always_xy=True)
        return transform(transformer.transform, geom)
