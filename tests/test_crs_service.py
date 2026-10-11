import pytest
from pyproj import CRS
from shapely.geometry import Point, Polygon
from app.services.crs_service import CRSService


def test_utm_zone_calculation():
    # Bengaluru / Ballari, India (~77° E, 13° N) -> UTM Zone 43N (EPSG:32643)
    epsg_india = CRSService.get_utm_epsg_for_latlon(13.0, 77.5)
    assert epsg_india == 32643

    # San Francisco, USA (~ -122.4° W, 37.8° N) -> UTM Zone 10N (EPSG:32610)
    epsg_sf = CRSService.get_utm_epsg_for_latlon(37.8, -122.4)
    assert epsg_sf == 32610

    # Sydney, Australia (~ 151.2° E, -33.8° S) -> UTM Zone 56S (EPSG:32756)
    epsg_sydney = CRSService.get_utm_epsg_for_latlon(-33.8, 151.2)
    assert epsg_sydney == 32756


def test_crs_parsing():
    # Valid EPSG code
    crs1 = CRSService.parse_crs("EPSG:4326")
    assert crs1.to_epsg() == 4326

    # None or empty fallback to EPSG:4326
    crs2 = CRSService.parse_crs(None)
    assert crs2.to_epsg() == 4326

    crs3 = CRSService.parse_crs("invalid_projection_string")
    assert crs3.to_epsg() == 4326


def test_get_projected_crs_for_geographic_geometry():
    source_crs = CRS.from_epsg(4326)
    # Polygon in Bengaluru (77.5, 12.9)
    poly = Polygon([[77.5, 12.9], [77.51, 12.9], [77.51, 12.91], [77.5, 12.91], [77.5, 12.9]])
    
    target_crs, name = CRSService.get_projected_crs_for_geometry(poly, source_crs)
    assert target_crs.to_epsg() == 32643
    assert "UTM Zone 43N" in name


def test_reproject_geometry():
    source_crs = CRS.from_epsg(4326)
    target_crs = CRS.from_epsg(32643)
    
    point_deg = Point(77.5, 13.0)
    point_m = CRSService.reproject_geometry(point_deg, source_crs, target_crs)
    
    # Coordinates in UTM should be in hundreds of thousands of meters
    assert point_m.x > 100_000
    assert point_m.y > 1_000_000
