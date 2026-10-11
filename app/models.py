from datetime import datetime
import json
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base


class FileRecord(Base):
    __tablename__ = "files"

    id = Column(String(36), primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    stored_path = Column(String(500), nullable=False)
    file_format = Column(String(50), nullable=False)  # "shapefile_zip" or "kml"
    file_size_bytes = Column(Integer, nullable=False, default=0)
    feature_count = Column(Integer, nullable=False, default=0)
    crs = Column(String(100), nullable=False, default="EPSG:4326")
    projected_crs = Column(String(100), nullable=True)
    status = Column(String(50), nullable=False, default="PENDING")  # PENDING, PROCESSING, COMPLETED, FAILED
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    features = relationship("FeatureRecord", back_populates="file", cascade="all, delete-orphan", order_by="FeatureRecord.feature_index")

    def to_dict(self):
        return {
            "id": self.id,
            "filename": self.filename,
            "feature_count": self.feature_count,
            "crs": self.crs,
            "projected_crs": self.projected_crs,
            "status": self.status,
            "file_size_bytes": self.file_size_bytes,
            "file_format": self.file_format,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class FeatureRecord(Base):
    __tablename__ = "features"

    id = Column(Integer, primary_key=True, autoincrement=True)
    file_id = Column(String(36), ForeignKey("files.id", ondelete="CASCADE"), nullable=False, index=True)
    feature_index = Column(Integer, nullable=False)
    feature_name = Column(String(255), nullable=True)
    geometry_type = Column(String(50), nullable=False)
    geometry_geojson = Column(Text, nullable=False)  # Raw GeoJSON geometry JSON string
    properties_json = Column(Text, nullable=False, default="{}")
    source_crs = Column(String(100), nullable=False, default="EPSG:4326")
    projected_crs = Column(String(100), nullable=True)
    
    # Measurements
    area_sq_meters = Column(Float, nullable=True)
    area_hectares = Column(Float, nullable=True)
    area_sq_km = Column(Float, nullable=True)
    length_meters = Column(Float, nullable=True)
    length_km = Column(Float, nullable=True)
    
    status = Column(String(50), nullable=False, default="CALCULATED")  # CALCULATED, SKIPPED, ERROR
    notes = Column(Text, nullable=True)

    # Relationships
    file = relationship("FileRecord", back_populates="features")

    def get_geometry_dict(self):
        try:
            return json.loads(self.geometry_geojson)
        except Exception:
            return {}

    def get_properties_dict(self):
        try:
            return json.loads(self.properties_json)
        except Exception:
            return {}

    def to_measurement_dict(self):
        measurement = {}
        if self.area_sq_meters is not None:
            measurement["area"] = {
                "square_meters": round(self.area_sq_meters, 2),
                "hectares": round(self.area_hectares, 4),
                "square_kilometers": round(self.area_sq_km, 6),
            }
        if self.length_meters is not None:
            measurement["length"] = {
                "meters": round(self.length_meters, 2),
                "kilometers": round(self.length_km, 4),
            }
        
        return {
            "feature_index": self.feature_index,
            "feature_name": self.feature_name,
            "geometry_type": self.geometry_type,
            "measurement": measurement if measurement else None,
            "projected_crs": self.projected_crs,
            "status": self.status,
            "notes": self.notes,
            "properties": self.get_properties_dict()
        }
