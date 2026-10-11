from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class FileResponse(BaseModel):
    id: str = Field(..., description="Unique file identifier")
    filename: str = Field(..., description="Original name of the uploaded file")
    feature_count: int = Field(..., description="Total number of geospatial features extracted")
    crs: str = Field(..., description="Source coordinate reference system, e.g. EPSG:4326")
    projected_crs: Optional[str] = Field(None, description="Projected CRS used for metric calculations (e.g., EPSG:32643 UTM)")
    status: str = Field(..., description="Processing status: PENDING, PROCESSING, COMPLETED, FAILED")
    file_format: Optional[str] = Field(None, description="Detected format: shapefile_zip or kml")
    file_size_bytes: Optional[int] = Field(None, description="File size in bytes")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp in ISO format")
    error_message: Optional[str] = Field(None, description="Error details if status is FAILED")

    model_config = ConfigDict(from_attributes=True)


class AreaMeasurement(BaseModel):
    square_meters: float
    hectares: float
    square_kilometers: float


class LengthMeasurement(BaseModel):
    meters: float
    kilometers: float


class MeasurementDetails(BaseModel):
    area: Optional[AreaMeasurement] = None
    length: Optional[LengthMeasurement] = None


class FeatureMeasurementItem(BaseModel):
    feature_index: int
    feature_name: Optional[str] = None
    geometry_type: str
    measurement: Optional[Dict[str, Any]] = None
    projected_crs: Optional[str] = None
    status: str
    notes: Optional[str] = None
    properties: Dict[str, Any] = Field(default_factory=dict)


class MeasurementsResponse(BaseModel):
    file_id: str
    filename: str
    feature_count: int
    source_crs: str
    projected_crs: Optional[str] = None
    status: str
    summary: Dict[str, Any] = Field(default_factory=dict, description="Aggregated metric totals (total area, total length)")
    features: List[FeatureMeasurementItem]


class GeoJSONFeature(BaseModel):
    type: str = "Feature"
    id: int
    geometry: Dict[str, Any]
    properties: Dict[str, Any]


class GeoJSONFeatureCollection(BaseModel):
    type: str = "FeatureCollection"
    file_id: str
    filename: str
    crs: str
    features: List[GeoJSONFeature]


class HealthResponse(BaseModel):
    status: str
    version: str
    supported_formats: List[str]
    capabilities: List[str]
