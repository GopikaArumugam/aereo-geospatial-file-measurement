import pytest
from pyproj import CRS
from shapely.geometry import Polygon, LineString, Point
from app.services.measurement import MeasurementService


def test_polygon_area_calculation():
    # Polygon in WGS84
    poly = Polygon([[77.580, 12.970], [77.585, 12.970], [77.585, 12.975], [77.580, 12.975], [77.580, 12.970]])
    source_crs = CRS.from_epsg(4326)

    res = MeasurementService.calculate_measurement(poly, source_crs)
    assert res.status == "CALCULATED"
    assert res.area_sq_meters is not None
    assert res.area_sq_meters > 0
    # 0.005 degrees is approx 540 meters -> area is approx ~290,000 m²
    assert 200_000 < res.area_sq_meters < 400_000
    assert res.area_hectares == res.area_sq_meters / 10_000.0
    assert res.area_sq_km == res.area_sq_meters / 1_000_000.0


def test_linestring_length_calculation():
    # LineString of approx 1 km in WGS84
    line = LineString([[77.580, 12.970], [77.589, 12.970]])
    source_crs = CRS.from_epsg(4326)

    res = MeasurementService.calculate_measurement(line, source_crs)
    assert res.status == "CALCULATED"
    assert res.length_meters is not None
    # 0.009 degrees of longitude at ~13 deg lat is approx 970 meters
    assert 800 < res.length_meters < 1200
    assert res.length_km == res.length_meters / 1000.0


def test_point_handling_skipped():
    pt = Point(77.580, 12.970)
    source_crs = CRS.from_epsg(4326)

    res = MeasurementService.calculate_measurement(pt, source_crs)
    assert res.status == "SKIPPED"
    assert res.area_sq_meters is None
    assert res.length_meters is None
    assert "Point geometry does not have measurable area or length" in res.notes


def test_self_intersecting_polygon_make_valid():
    # Bow-tie polygon (self-intersecting)
    bow_tie = Polygon([[0, 0], [2, 2], [2, 0], [0, 2], [0, 0]])
    source_crs = CRS.from_epsg(4326)

    # make_valid repairs this into a MultiPolygon
    res = MeasurementService.calculate_measurement(bow_tie, source_crs)
    assert res.status == "CALCULATED"
    assert res.area_sq_meters is not None
    assert res.area_sq_meters > 0
