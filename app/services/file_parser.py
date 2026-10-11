import os
import shutil
import tempfile
import zipfile
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import shapefile
from shapely.geometry import shape, mapping, Polygon, LineString, Point, MultiPolygon, MultiLineString, MultiPoint, GeometryCollection
from shapely.geometry.base import BaseGeometry
from pyproj import CRS
from app.services.crs_service import CRSService


class ParsedFeature:
    def __init__(
        self,
        feature_index: int,
        feature_name: Optional[str],
        geometry: BaseGeometry,
        geometry_geojson: Dict[str, Any],
        geometry_type: str,
        properties: Dict[str, Any],
        source_crs: str
    ):
        self.feature_index = feature_index
        self.feature_name = feature_name
        self.geometry = geometry
        self.geometry_geojson = geometry_geojson
        self.geometry_type = geometry_type
        self.properties = properties
        self.source_crs = source_crs


class ParsedDataset:
    def __init__(
        self,
        filename: str,
        file_format: str,
        source_crs: str,
        features: List[ParsedFeature],
        overall_projected_crs: Optional[str] = None
    ):
        self.filename = filename
        self.file_format = file_format
        self.source_crs = source_crs
        self.features = features
        self.overall_projected_crs = overall_projected_crs


class FileParser:
    """
    Parses geospatial files (.zip containing Shapefile or .kml).
    Extracts features, geometry types, attributes, and source CRS.
    """

    @classmethod
    def parse_file(cls, file_path: Path, filename: str) -> ParsedDataset:
        suffix = file_path.suffix.lower()
        if suffix == ".zip":
            return cls.parse_shapefile_zip(file_path, filename)
        elif suffix == ".kml":
            return cls.parse_kml_file(file_path, filename)
        else:
            raise ValueError(f"Unsupported file format: '{suffix}'. Supported formats are .zip (Shapefile) and .kml")

    # -------------------------------------------------------------------------
    # Shapefile (.zip) Parser
    # -------------------------------------------------------------------------
    @classmethod
    def parse_shapefile_zip(cls, zip_path: Path, filename: str) -> ParsedDataset:
        temp_dir = tempfile.mkdtemp(prefix="aereo_shp_")
        try:
            with zipfile.ZipFile(zip_path, 'r') as z:
                # Filter out macOS metadata files
                file_list = [f for f in z.namelist() if not f.startswith("__MACOSX/") and not f.startswith(".")]
                z.extractall(temp_dir, members=file_list)

            # Find .shp file
            shp_files = list(Path(temp_dir).rglob("*.shp"))
            if not shp_files:
                raise ValueError("No .shp file found inside the uploaded zip archive.")
            
            target_shp = shp_files[0]
            base_stem = target_shp.stem
            
            # Check for .prj file to detect CRS
            prj_file = target_shp.parent / f"{base_stem}.prj"
            source_crs_str = "EPSG:4326"
            if prj_file.exists():
                try:
                    wkt_text = prj_file.read_text(encoding="utf-8", errors="ignore").strip()
                    if wkt_text:
                        parsed_crs = CRS.from_wkt(wkt_text)
                        # Try to format as EPSG if available, else WKT representation
                        epsg = parsed_crs.to_epsg()
                        source_crs_str = f"EPSG:{epsg}" if epsg else parsed_crs.to_string()
                except Exception:
                    source_crs_str = "EPSG:4326"

            # Open with pyshp
            parsed_features: List[ParsedFeature] = []
            with shapefile.Reader(str(target_shp), encoding="utf-8", encodingErrors="replace") as sf:
                fields = [f[0] for f in sf.fields[1:]]  # exclude DeletionFlag
                
                for idx, shape_rec in enumerate(sf.shapeRecords()):
                    # Extract attributes
                    record_dict = {}
                    for field_name, value in zip(fields, shape_rec.record):
                        if isinstance(value, bytes):
                            try:
                                value = value.decode("utf-8")
                            except UnicodeDecodeError:
                                value = value.decode("latin1", errors="replace")
                        record_dict[field_name] = value

                    # Extract name candidate
                    feature_name = None
                    for key in ["name", "Name", "NAME", "id", "ID", "title", "label"]:
                        if key in record_dict and record_dict[key]:
                            feature_name = str(record_dict[key])
                            break
                    if not feature_name:
                        feature_name = f"Feature #{idx + 1}"

                    # Convert to Shapely geometry
                    geo_interface = shape_rec.shape.__geo_interface__
                    try:
                        shapely_geom = shape(geo_interface)
                    except Exception as e:
                        # Fallback for null or malformed shapes
                        shapely_geom = GeometryCollection()

                    geom_type = shapely_geom.geom_type
                    geom_geojson = mapping(shapely_geom)

                    parsed_features.append(ParsedFeature(
                        feature_index=idx,
                        feature_name=feature_name,
                        geometry=shapely_geom,
                        geometry_geojson=geom_geojson,
                        geometry_type=geom_type,
                        properties=record_dict,
                        source_crs=source_crs_str
                    ))

            # Determine dominant projected CRS for summary
            sample_projected = None
            if parsed_features:
                source_crs_obj = CRSService.parse_crs(source_crs_str)
                for pf in parsed_features:
                    if not pf.geometry.is_empty:
                        _, sample_projected = CRSService.get_projected_crs_for_geometry(pf.geometry, source_crs_obj)
                        break

            return ParsedDataset(
                filename=filename,
                file_format="shapefile_zip",
                source_crs=source_crs_str,
                features=parsed_features,
                overall_projected_crs=sample_projected
            )

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    # -------------------------------------------------------------------------
    # KML Parser
    # -------------------------------------------------------------------------
    @classmethod
    def parse_kml_file(cls, kml_path: Path, filename: str) -> ParsedDataset:
        tree = ET.parse(str(kml_path))
        root = tree.getroot()

        # Handle XML namespaces dynamically
        def strip_ns(tag):
            return tag.split('}')[-1] if '}' in tag else tag

        source_crs_str = "EPSG:4326"  # KML specification mandates WGS84
        parsed_features: List[ParsedFeature] = []

        # Find all Placemark elements regardless of nesting
        placemarks = [elem for elem in root.iter() if strip_ns(elem.tag) == "Placemark"]

        for idx, pm in enumerate(placemarks):
            # Extract Placemark name and description
            name_elem = next((e for e in pm if strip_ns(e.tag) == "name"), None)
            desc_elem = next((e for e in pm if strip_ns(e.tag) == "description"), None)
            
            feature_name = name_elem.text.strip() if (name_elem is not None and name_elem.text) else f"Placemark #{idx + 1}"
            description = desc_elem.text.strip() if (desc_elem is not None and desc_elem.text) else ""

            properties: Dict[str, Any] = {
                "name": feature_name,
                "description": description
            }

            # Parse ExtendedData if present
            ext_data = next((e for e in pm if strip_ns(e.tag) == "ExtendedData"), None)
            if ext_data is not None:
                for data_elem in ext_data:
                    data_tag = strip_ns(data_elem.tag)
                    if data_tag == "Data":
                        attr_name = data_elem.attrib.get("name")
                        val_elem = next((e for e in data_elem if strip_ns(e.tag) == "value"), None)
                        if attr_name and val_elem is not None and val_elem.text:
                            properties[attr_name] = val_elem.text.strip()
                    elif data_tag == "SimpleData":
                        attr_name = data_elem.attrib.get("name")
                        if attr_name and data_elem.text:
                            properties[attr_name] = data_elem.text.strip()

            # Parse Geometries
            shapely_geom = cls._extract_kml_geometry(pm, strip_ns)
            geom_type = shapely_geom.geom_type if shapely_geom else "Unknown"
            geom_geojson = mapping(shapely_geom) if shapely_geom else {}

            parsed_features.append(ParsedFeature(
                feature_index=idx,
                feature_name=feature_name,
                geometry=shapely_geom,
                geometry_geojson=geom_geojson,
                geometry_type=geom_type,
                properties=properties,
                source_crs=source_crs_str
            ))

        # Determine dominant projected CRS for summary
        sample_projected = None
        if parsed_features:
            source_crs_obj = CRSService.parse_crs(source_crs_str)
            for pf in parsed_features:
                if not pf.geometry.is_empty:
                    _, sample_projected = CRSService.get_projected_crs_for_geometry(pf.geometry, source_crs_obj)
                    break

        return ParsedDataset(
            filename=filename,
            file_format="kml",
            source_crs=source_crs_str,
            features=parsed_features,
            overall_projected_crs=sample_projected
        )

    @classmethod
    def _parse_coord_string(cls, text: str) -> List[Tuple[float, float]]:
        """Parses KML coordinate text 'lon,lat,alt lon,lat,alt' into [(lon, lat), ...]"""
        coords = []
        if not text:
            return coords
        
        # Split by whitespace or newlines
        tokens = text.strip().split()
        for token in tokens:
            parts = token.split(',')
            if len(parts) >= 2:
                try:
                    lon = float(parts[0])
                    lat = float(parts[1])
                    coords.append((lon, lat))
                except ValueError:
                    continue
        return coords

    @classmethod
    def _extract_kml_geometry(cls, element: ET.Element, strip_ns) -> BaseGeometry:
        """Extracts Polygon, LineString, Point, or MultiGeometry from a KML element."""
        geoms = []

        for child in element.iter():
            tag = strip_ns(child.tag)
            
            # Point
            if tag == "Point":
                coords_elem = next((e for e in child if strip_ns(e.tag) == "coordinates"), None)
                if coords_elem is not None and coords_elem.text:
                    parsed = cls._parse_coord_string(coords_elem.text)
                    if parsed:
                        geoms.append(Point(parsed[0]))

            # LineString
            elif tag == "LineString":
                coords_elem = next((e for e in child if strip_ns(e.tag) == "coordinates"), None)
                if coords_elem is not None and coords_elem.text:
                    parsed = cls._parse_coord_string(coords_elem.text)
                    if len(parsed) >= 2:
                        geoms.append(LineString(parsed))

            # Polygon
            elif tag == "Polygon":
                outer_coords = []
                inner_rings = []
                
                for p_child in child:
                    p_tag = strip_ns(p_child.tag)
                    if p_tag == "outerBoundaryIs":
                        lr = next((e for e in p_child if strip_ns(e.tag) == "LinearRing"), None)
                        if lr is not None:
                            c_elem = next((e for e in lr if strip_ns(e.tag) == "coordinates"), None)
                            if c_elem is not None and c_elem.text:
                                outer_coords = cls._parse_coord_string(c_elem.text)
                    elif p_tag == "innerBoundaryIs":
                        lr = next((e for e in p_child if strip_ns(e.tag) == "LinearRing"), None)
                        if lr is not None:
                            c_elem = next((e for e in lr if strip_ns(e.tag) == "coordinates"), None)
                            if c_elem is not None and c_elem.text:
                                inner_c = cls._parse_coord_string(c_elem.text)
                                if len(inner_c) >= 3:
                                    inner_rings.append(inner_c)
                
                if len(outer_coords) >= 3:
                    try:
                        geoms.append(Polygon(outer_coords, inner_rings))
                    except Exception:
                        pass

        if not geoms:
            return GeometryCollection()
        elif len(geoms) == 1:
            return geoms[0]
        else:
            # Check if all same type for Multi*
            if all(isinstance(g, Polygon) for g in geoms):
                return MultiPolygon(geoms)
            elif all(isinstance(g, LineString) for g in geoms):
                return MultiLineString(geoms)
            elif all(isinstance(g, Point) for g in geoms):
                return MultiPoint(geoms)
            else:
                return GeometryCollection(geoms)
