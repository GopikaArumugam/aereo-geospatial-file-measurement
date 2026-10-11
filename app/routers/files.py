import os
import uuid
import json
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models import FileRecord, FeatureRecord
from app.schemas import (
    FileResponse,
    MeasurementsResponse,
    FeatureMeasurementItem,
    GeoJSONFeatureCollection,
    GeoJSONFeature
)
from app.services.file_parser import FileParser
from app.services.crs_service import CRSService
from app.services.measurement import MeasurementService

router = APIRouter(prefix="/files", tags=["Files"])


@router.post("/", response_model=FileResponse, status_code=status.HTTP_201_CREATED)
async def upload_and_process_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload and process a geospatial file (.zip containing Shapefile or .kml).
    
    1. Validates file extension and size.
    2. Stores the file securely.
    3. Extracts spatial features, geometries, attributes, and source CRS.
    4. Transforms geometries into an appropriate metric projected coordinate system (UTM).
    5. Calculates area for Polygons and length for LineStrings.
    6. Persists metadata and measurements.
    """
    original_filename = file.filename or "unknown"
    suffix = Path(original_filename).suffix.lower()

    if suffix not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{suffix}'. Allowed formats: {list(settings.ALLOWED_EXTENSIONS)}"
        )

    file_id = uuid.uuid4().hex[:12]
    stored_filename = f"{file_id}_{original_filename}"
    destination_path = settings.UPLOAD_DIR / stored_filename

    # Stream file to disk
    file_size = 0
    try:
        with open(destination_path, "wb") as buffer:
            while chunk := await file.read(1024 * 1024):  # 1MB chunks
                file_size += len(chunk)
                if file_size > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"File exceeds maximum allowed size of {settings.MAX_FILE_SIZE_MB}MB"
                    )
                buffer.write(chunk)
    except Exception as e:
        if destination_path.exists():
            destination_path.unlink()
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded file: {str(e)}")

    # Create initial database record
    file_record = FileRecord(
        id=file_id,
        filename=original_filename,
        stored_path=str(destination_path),
        file_format="shapefile_zip" if suffix == ".zip" else "kml",
        file_size_bytes=file_size,
        status="PROCESSING"
    )
    db.add(file_record)
    db.commit()
    db.refresh(file_record)

    # Process geospatial data
    try:
        parsed_dataset = FileParser.parse_file(destination_path, original_filename)
        source_crs_obj = CRSService.parse_crs(parsed_dataset.source_crs)

        dominant_projected_crs = parsed_dataset.overall_projected_crs

        # Process each feature
        for pf in parsed_dataset.features:
            meas_res = MeasurementService.calculate_measurement(pf.geometry, source_crs_obj)
            
            if not dominant_projected_crs and meas_res.projected_crs_name:
                dominant_projected_crs = meas_res.projected_crs_name

            feat_record = FeatureRecord(
                file_id=file_id,
                feature_index=pf.feature_index,
                feature_name=pf.feature_name,
                geometry_type=pf.geometry_type,
                geometry_geojson=json.dumps(pf.geometry_geojson),
                properties_json=json.dumps(pf.properties),
                source_crs=pf.source_crs,
                projected_crs=meas_res.projected_crs_name,
                area_sq_meters=meas_res.area_sq_meters,
                area_hectares=meas_res.area_hectares,
                area_sq_km=meas_res.area_sq_km,
                length_meters=meas_res.length_meters,
                length_km=meas_res.length_km,
                status=meas_res.status,
                notes=meas_res.notes
            )
            db.add(feat_record)

        # Update file record
        file_record.feature_count = len(parsed_dataset.features)
        file_record.crs = parsed_dataset.source_crs
        file_record.projected_crs = dominant_projected_crs
        file_record.status = "COMPLETED"
        db.commit()
        db.refresh(file_record)

        return file_record

    except Exception as e:
        db.rollback()
        file_record.status = "FAILED"
        file_record.error_message = str(e)
        db.commit()
        db.refresh(file_record)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Error processing geospatial file: {str(e)}"
        )


@router.get("/{id}/", response_model=FileResponse)
def get_file_info(id: str, db: Session = Depends(get_db)):
    """
    Returns metadata and status for a specific uploaded file.
    """
    file_record = db.query(FileRecord).filter(FileRecord.id == id).first()
    if not file_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"File with id '{id}' not found")
    return file_record


@router.get("/{id}/measurements/", response_model=MeasurementsResponse)
def get_file_measurements(id: str, db: Session = Depends(get_db)):
    """
    Returns calculated measurements (Area, Length) for all features within the specified file.
    """
    file_record = db.query(FileRecord).filter(FileRecord.id == id).first()
    if not file_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"File with id '{id}' not found")

    features = db.query(FeatureRecord).filter(FeatureRecord.file_id == id).order_by(FeatureRecord.feature_index).all()

    total_area_m2 = sum(f.area_sq_meters for f in features if f.area_sq_meters is not None)
    total_len_m = sum(f.length_meters for f in features if f.length_meters is not None)

    summary = {
        "total_area_sq_meters": round(total_area_m2, 2) if total_area_m2 > 0 else 0.0,
        "total_area_hectares": round(total_area_m2 / 10_000.0, 4) if total_area_m2 > 0 else 0.0,
        "total_length_meters": round(total_len_m, 2) if total_len_m > 0 else 0.0,
        "total_length_km": round(total_len_m / 1_000.0, 4) if total_len_m > 0 else 0.0,
        "features_calculated": sum(1 for f in features if f.status == "CALCULATED"),
        "features_skipped": sum(1 for f in features if f.status == "SKIPPED"),
        "features_unsupported_or_error": sum(1 for f in features if f.status in ("UNSUPPORTED", "ERROR", "INVALID"))
    }

    feature_items = [
        FeatureMeasurementItem(
            feature_index=f.feature_index,
            feature_name=f.feature_name,
            geometry_type=f.geometry_type,
            measurement=f.to_measurement_dict().get("measurement"),
            projected_crs=f.projected_crs,
            status=f.status,
            notes=f.notes,
            properties=f.get_properties_dict()
        )
        for f in features
    ]

    return MeasurementsResponse(
        file_id=file_record.id,
        filename=file_record.filename,
        feature_count=file_record.feature_count,
        source_crs=file_record.crs,
        projected_crs=file_record.projected_crs,
        status=file_record.status,
        summary=summary,
        features=feature_items
    )


@router.get("/{id}/features/", response_model=GeoJSONFeatureCollection)
def get_file_geojson(id: str, db: Session = Depends(get_db)):
    """
    Returns features in standard GeoJSON FeatureCollection format for interactive map visualization.
    """
    file_record = db.query(FileRecord).filter(FileRecord.id == id).first()
    if not file_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"File with id '{id}' not found")

    features = db.query(FeatureRecord).filter(FeatureRecord.file_id == id).order_by(FeatureRecord.feature_index).all()

    geojson_features = []
    for f in features:
        props = f.get_properties_dict()
        props["_feature_index"] = f.feature_index
        props["_feature_name"] = f.feature_name
        props["_geometry_type"] = f.geometry_type
        props["_status"] = f.status
        props["_notes"] = f.notes
        if f.area_sq_meters is not None:
            props["_area_sq_meters"] = round(f.area_sq_meters, 2)
            props["_area_hectares"] = round(f.area_hectares, 4)
        if f.length_meters is not None:
            props["_length_meters"] = round(f.length_meters, 2)
            props["_length_km"] = round(f.length_km, 4)

        geojson_features.append(GeoJSONFeature(
            type="Feature",
            id=f.id,
            geometry=f.get_geometry_dict(),
            properties=props
        ))

    return GeoJSONFeatureCollection(
        type="FeatureCollection",
        file_id=file_record.id,
        filename=file_record.filename,
        crs=file_record.crs,
        features=geojson_features
    )


@router.get("/", response_model=List[FileResponse])
def list_files(db: Session = Depends(get_db)):
    """
    Lists all processed files ordered by most recent.
    """
    return db.query(FileRecord).order_by(FileRecord.created_at.desc()).all()


@router.delete("/{id}/", status_code=status.HTTP_204_NO_CONTENT)
def delete_file(id: str, db: Session = Depends(get_db)):
    """
    Deletes a file, its extracted features, and local disk assets.
    """
    file_record = db.query(FileRecord).filter(FileRecord.id == id).first()
    if not file_record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"File with id '{id}' not found")

    # Delete local file
    try:
        disk_path = Path(file_record.stored_path)
        if disk_path.exists():
            disk_path.unlink()
    except Exception:
        pass

    db.delete(file_record)
    db.commit()
    return None
