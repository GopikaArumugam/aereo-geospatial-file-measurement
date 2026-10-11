from pathlib import Path
import pytest
from fastapi.testclient import TestClient

SAMPLE_DIR = Path("sample_data")


def test_health_check(client: TestClient):
    response = client.get("/api/health/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert len(data["supported_formats"]) > 0


def test_upload_invalid_extension(client: TestClient):
    files = {"file": ("test.txt", b"invalid content", "text/plain")}
    response = client.post("/api/files/", files=files)
    assert response.status_code == 400
    assert "Unsupported file format" in response.json()["detail"]


def test_upload_and_process_kml(client: TestClient):
    kml_path = SAMPLE_DIR / "sample_mining_pit.kml"
    with open(kml_path, "rb") as f:
        response = client.post(
            "/api/files/",
            files={"file": ("sample_mining_pit.kml", f, "application/vnd.google-earth.kml+xml")}
        )

    assert response.status_code == 201
    file_data = response.json()
    assert file_data["status"] == "COMPLETED"
    assert file_data["filename"] == "sample_mining_pit.kml"
    assert file_data["feature_count"] == 5
    assert file_data["crs"] == "EPSG:4326"
    assert "UTM Zone 43N" in file_data["projected_crs"]

    file_id = file_data["id"]

    # 1. Test GET /api/files/{id}/
    info_res = client.get(f"/api/files/{file_id}/")
    assert info_res.status_code == 200
    assert info_res.json()["id"] == file_id

    # 2. Test GET /api/files/{id}/measurements/
    meas_res = client.get(f"/api/files/{file_id}/measurements/")
    assert meas_res.status_code == 200
    meas_data = meas_res.json()
    assert meas_data["file_id"] == file_id
    assert meas_data["summary"]["total_area_sq_meters"] > 0
    assert meas_data["summary"]["total_length_meters"] > 0
    assert len(meas_data["features"]) == 5

    # 3. Test GET /api/files/{id}/features/ (GeoJSON)
    geo_res = client.get(f"/api/files/{file_id}/features/")
    assert geo_res.status_code == 200
    geo_data = geo_res.json()
    assert geo_data["type"] == "FeatureCollection"
    assert len(geo_data["features"]) == 5

    # 4. Test DELETE /api/files/{id}/
    del_res = client.delete(f"/api/files/{file_id}/")
    assert del_res.status_code == 204

    # Verify 404 after deletion
    after_del_res = client.get(f"/api/files/{file_id}/")
    assert after_del_res.status_code == 404


def test_upload_and_process_shapefile_zip(client: TestClient):
    shp_path = SAMPLE_DIR / "sample_corridor_survey.zip"
    with open(shp_path, "rb") as f:
        response = client.post(
            "/api/files/",
            files={"file": ("sample_corridor_survey.zip", f, "application/zip")}
        )

    assert response.status_code == 201
    file_data = response.json()
    assert file_data["status"] == "COMPLETED"
    assert file_data["feature_count"] == 2
    assert "UTM" in file_data["projected_crs"]

    file_id = file_data["id"]

    # Test measurements
    meas_res = client.get(f"/api/files/{file_id}/measurements/")
    assert meas_res.status_code == 200
    meas_data = meas_res.json()
    assert meas_data["summary"]["total_area_sq_meters"] > 0
    assert meas_data["summary"]["features_calculated"] == 2


def test_get_nonexistent_file_404(client: TestClient):
    response = client.get("/api/files/nonexistent_id/")
    assert response.status_code == 404
