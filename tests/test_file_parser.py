from pathlib import Path
import pytest
from app.services.file_parser import FileParser

SAMPLE_DIR = Path("sample_data")


def test_parse_kml_file():
    kml_path = SAMPLE_DIR / "sample_mining_pit.kml"
    assert kml_path.exists(), "Sample KML must exist"

    dataset = FileParser.parse_file(kml_path, "sample_mining_pit.kml")
    assert dataset.file_format == "kml"
    assert dataset.source_crs == "EPSG:4326"
    assert len(dataset.features) == 5

    # Check extracted geometry types
    geom_types = [f.geometry_type for f in dataset.features]
    assert "Polygon" in geom_types
    assert "LineString" in geom_types
    assert "Point" in geom_types

    # Check properties
    names = [f.feature_name for f in dataset.features]
    assert any("Pit Extraction" in n for n in names)
    assert any("Primary Haul Road" in n for n in names)


def test_parse_shapefile_zip():
    shp_zip = SAMPLE_DIR / "sample_corridor_survey.zip"
    assert shp_zip.exists(), "Sample Shapefile zip must exist"

    dataset = FileParser.parse_file(shp_zip, "sample_corridor_survey.zip")
    assert dataset.file_format == "shapefile_zip"
    assert "EPSG:4326" in dataset.source_crs
    assert len(dataset.features) == 2

    for f in dataset.features:
        assert f.geometry_type == "Polygon"
        assert "Solar Farm" in f.feature_name or "Substation" in f.feature_name
