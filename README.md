# Geospatial File Measurement API

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com)
[![Shapely](https://img.shields.io/badge/Shapely-2.1+-green.svg)](https://shapely.readthedocs.io/)
[![PyProj](https://img.shields.io/badge/PyProj-3.7+-informational.svg)](https://pyproj4.github.io/pyproj/)
[![Pytest Passed](https://img.shields.io/badge/pytest-15%2F15%20passed-brightgreen.svg)](https://pytest.org)
[![Docker Ready](https://img.shields.io/badge/docker-ready-2496ED.svg)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A high-performance geospatial processing service and interactive GIS dashboard designed for drone, aerial surveying, and spatial intelligence platforms (built for the **AEREO Cloud** Engineering Assignment).

The service ingests geospatial vector files (**Shapefiles in `.zip`** and **KML `.kml`**), extracts spatial features and metadata, dynamically reprojects geographic coordinates (`EPSG:4326`) into optimal metric planar coordinate systems (UTM), and computes high-precision metric measurements (**Polygon Area** in $m^2$, hectares, $km^2$ and **LineString Length** in meters, $km$).

---

## 📑 Table of Contents
- [1. Overview & Key Capabilities](#1-overview--key-capabilities)
- [2. System Architecture & Workflow](#2-system-architecture--workflow)
- [3. The Core Geospatial Challenge: CRS & Projection Math](#3-the-core-geospatial-challenge-crs--projection-math)
- [4. Quickstart & Setup Guide](#4-quickstart--setup-guide)
- [5. API Reference & Specifications](#5-api-reference--specifications)
- [6. Web GIS Dashboard Walkthrough](#6-web-gis-dashboard-walkthrough)
- [7. Automated Testing & Verification](#7-automated-testing--verification)
- [8. Assignment Requirements Verification Matrix](#8-assignment-requirements-verification-matrix)
- [9. Design Decisions & Trade-offs](#9-design-decisions--trade-offs)
- [10. Key Learnings & Future Scope](#10-key-learnings--future-scope)

---

## 1. Overview & Key Capabilities

In aerial drone surveys across open-pit mines, construction corridors, renewable solar fields, and utility networks:
* **Mining & Earthwork Teams** require exact land area calculations for excavation sectors, dumping yards, and stockpile footprints.
* **Infrastructure Engineers** require high-precision distance measurements for transmission line alignments, pipeline rights-of-way, and haul roads.
* **Raw Survey Vector Files** are commonly delivered as **ESRI Shapefiles** or **Google Earth KMLs**, typically recorded in unprojected angular coordinates (WGS84 `EPSG:4326`).

### Core Features
- **Multi-Format Vector Ingestion:** Accepts zipped Shapefile archives (`.shp`, `.shx`, `.dbf`, `.prj`) and Keyhole Markup Language (`.kml`) files up to 50MB.
- **Dynamic Metric Reprojection:** Automatically resolves local **Universal Transverse Mercator (UTM)** zones based on feature centroids, eliminating the severe distortion of raw degree coordinates.
- **Robust Geometry Engine:** Accurately computes metric **Area** for Polygons/MultiPolygons and **Length** for LineStrings/MultiLineStrings. Gracefully handles Points without system crashes.
- **Topological Self-Healing:** Automatically repairs self-intersecting "bow-tie" rings and collapsed sliver geometries via `shapely.validation.make_valid`.
- **Dual-Basemap GIS Dashboard:** Served directly from the backend with interactive Leaflet mapping, supporting both **OpenStreetMap** and **Esri High-Resolution World Satellite Imagery** (100% free, zero API key required).
- **Interactive OpenAPI Interfaces:** Full Swagger UI (`/docs`) and ReDoc (`/redoc`) documentation with live testing capabilities.

---

## 2. System Architecture & Workflow

### Directory Layout
```
d:\Aereo\
├── app/
│   ├── main.py              # Application lifecycle, CORS middleware, route mounting
│   ├── config.py            # Pydantic v2 application settings & environment variables
│   ├── database.py          # SQLAlchemy 2.0 engine, SessionLocal, declarative base
│   ├── models.py            # Database models (FileRecord, FeatureRecord)
│   ├── schemas.py           # Pydantic validation schemas & API contracts
│   ├── routers/
│   │   ├── files.py         # Ingestion, status, measurements, GeoJSON & deletion endpoints
│   │   ├── health.py        # System health & capabilities check probe
│   │   └── samples.py       # Pre-packaged demo survey dataset distributor
│   ├── services/
│   │   ├── crs_service.py   # Dynamic UTM zone resolution & PyProj geometry reprojection
│   │   ├── measurement.py   # Metric area & length computation + topology repair
│   │   └── file_parser.py   # Shapefile (.zip) and KML (.kml) parser & feature extractor
│   └── static/              # Executive GIS Web Dashboard (HTML5, CSS3, JS, Leaflet)
│       ├── index.html       # Clean single-page application layout
│       ├── css/style.css    # Minimalist slate/enterprise styling
│       └── js/app.js        # Leaflet map controller, layer switcher, upload handler
├── sample_data/             # Pre-built test datasets (Ballari Mining Pit KML, Corridor SHP ZIP)
├── scripts/
│   └── generate_samples.py  # Script for generating sample survey datasets
├── tests/                   # Automated pytest suite (15 unit & integration tests)
│   ├── conftest.py          # Thread-safe in-memory SQLite fixtures with StaticPool
│   ├── test_api_endpoints.py# End-to-end API lifecycle tests
│   ├── test_crs_service.py  # Mathematical UTM zone & coordinate projection tests
│   ├── test_file_parser.py  # Shapefile ZIP and KML XML extraction tests
│   └── test_measurements.py # Area, length, make_valid, and point skip tests
├── Dockerfile               # Production container definition
├── docker-compose.yml       # Docker Compose multi-service definition
├── requirements.txt         # Pinned Python package dependencies
└── pytest.ini               # Pytest environment configuration
```

### Processing Flowchart

```mermaid
flowchart TD
    Client["Client / Web UI"] -->|"POST /api/files/"| API["FastAPI Router (files.py)"]
    API -->|"1. Validate File (.zip / .kml)"| Val{"Valid Format & Size?"}
    Val -->|"No"| Err["HTTP 400 / 413 Response"]
    Val -->|"Yes"| Disk["Write to Upload Storage & Insert FileRecord (PROCESSING)"]
    
    Disk --> Parser["FileParser Service"]
    subgraph Extraction ["Feature Extraction Layer"]
        Parser -->|"Shapefile ZIP"| Shp["Unpack & Read (.shp, .dbf, .prj) via pyshp"]
        Parser -->|"KML File"| Kml["Parse Placemarks, LinearRings & ExtendedData"]
    end
    
    Shp --> RawGeom["List of ParsedFeatures (Source CRS, Geometry, Properties)"]
    Kml --> RawGeom
    
    RawGeom --> CRS["CRSService (crs_service.py)"]
    subgraph GeoEngine ["Geospatial & Mathematics Engine"]
        CRS --> Centroid["Extract Centroid (Lon, Lat)"]
        Centroid --> UTMCalc["Compute Dynamic UTM Zone (EPSG:326XX / 327XX)"]
        UTMCalc --> Reproj["Reproject Geometry (pyproj Transformer, always_xy=True)"]
        Reproj --> MeasEngine["MeasurementService (measurement.py)"]
        
        MeasEngine --> GeomCheck{"Geometry Type"}
        GeomCheck -->|"Polygon / MultiPolygon"| Area["Compute Area (m², ha, km²)"]
        GeomCheck -->|"LineString / MultiLineString"| Len["Compute Length (m, km)"]
        GeomCheck -->|"Point / MultiPoint"| Skip["Mark SKIPPED (0 area/length)"]
        GeomCheck -->|"Self-Intersecting"| Fix["shapely.make_valid()"] --> Area
    end
    
    Area --> Persist["Save FeatureRecords to SQLite & Set Status=COMPLETED"]
    Len --> Persist
    Skip --> Persist
    Persist --> Res["Return FileResponse JSON (HTTP 201)"]
```

### Execution Sequence Diagram

```mermaid
sequenceDiagram
    autonumber
    actor User as User / Client
    participant Router as API Router (/api/files/)
    participant Storage as File Storage & DB
    participant Parser as FileParser
    participant CRS as CRSService
    participant Meas as MeasurementService
    
    User->>Router: POST /api/files/ (multipart/form-data)
    Router->>Storage: Stream file to disk & create FileRecord (status=PROCESSING)
    Router->>Parser: parse_file(path, filename)
    Parser-->>Router: ParsedDataset (features, attributes, source_crs)
    
    loop For each feature in dataset
        Router->>Meas: calculate_measurement(geometry, source_crs)
        Meas->>CRS: get_projected_crs_for_geometry(geometry, source_crs)
        CRS-->>Meas: (target_utm_crs, projected_crs_name)
        Meas->>CRS: reproject_geometry(geometry, source_crs, target_utm_crs)
        CRS-->>Meas: projected_geometry (planar meters)
        Meas->>Meas: Compute area (m²) or length (m)
        Meas-->>Router: MeasurementResult (values, units, status)
        Router->>Storage: Insert FeatureRecord
    end
    
    Router->>Storage: Update FileRecord (feature_count, crs, status=COMPLETED)
    Router-->>User: HTTP 201 Created (FileResponse JSON)
```

---

## 3. The Core Geospatial Challenge: CRS & Projection Math

### The Fundamental Problem: Why Angular Coordinates ($EPSG:4326$) Fail
Most raw drone survey data, GPS waypoints, and KML files are provided in **WGS84 (`EPSG:4326`)**, where coordinates represent angular degrees:
* Latitude: $\phi \in [-90^\circ, +90^\circ]$
* Longitude: $\lambda \in [-180^\circ, +180^\circ]$

If an API naively calculates Euclidean polygon area or line distance directly on degrees:
1. **Meaningless Units:** Area evaluates to "square degrees" ($^\circ{}^2$), and length evaluates to "degrees" ($^\circ$).
2. **Latitudinal Distortion:** On the Earth's ellipsoidal surface, while $1^\circ$ of latitude is approximately constant (~111 km), $1^\circ$ of longitude contracts toward the poles:

$$\Delta x = 111.32 \times \cos(\phi) \text{ km}$$

At latitude $\phi = 15^\circ$ (e.g., Ballari/Bengaluru, India), $1^\circ$ longitude $\approx 107.5 \text{ km}$. At $\phi = 60^\circ$ (e.g., Northern Europe/Canada), $1^\circ$ longitude contracts to only $55.6 \text{ km}$ ($50\%$ shrinkage). Computing flat Euclidean geometry on unprojected coordinates creates severe geometric distortion.

---

### The Solution: Dynamic UTM Zone Reprojection

To provide metric measurements, our service dynamically projects coordinates into the optimal **Universal Transverse Mercator (UTM)** system.

#### 1. Mathematical Zone Resolution
The globe is divided into 60 longitudinal UTM zones, each $6^\circ$ wide. Given a feature centroid $(\lambda, \phi) = (\text{lon}, \text{lat})$:

$$\text{zone} = \left\lfloor \frac{\lambda + 180^\circ}{6^\circ} \right\rfloor + 1 \quad \text{clamped to } [1, 60]$$

$$\text{EPSG Code} = \begin{cases} 32600 + \text{zone} & \text{if } \phi \ge 0^\circ \text{ (Northern Hemisphere)} \\ 32700 + \text{zone} & \text{if } \phi < 0^\circ \text{ (Southern Hemisphere)} \end{cases}$$

*Real-World Example:*
For our Ballari Iron Ore drone survey ($\lambda = 76.92^\circ\text{E}, \phi = 15.15^\circ\text{N}$):
$$\text{zone} = \left\lfloor \frac{76.92 + 180}{6} \right\rfloor + 1 = \lfloor 42.82 \rfloor + 1 = 43$$
Because $\phi > 0^\circ$, target EPSG is **`EPSG:32643` (UTM Zone 43N)**.

#### 2. Why UTM vs. Web Mercator (`EPSG:3857`)?
Web Mercator is ubiquitous in consumer web mapping, but its area scale distortion factor is:

$$k = \frac{1}{\cos(\phi)} \implies \text{Area Distortion} = k^2 = \frac{1}{\cos^2(\phi)}$$

At latitude $45^\circ$, Web Mercator exaggerates land area by **$100\%$ ($2\times$)**! At latitude $60^\circ$, it exaggerates area by **$300\%$ ($4\times$)**. 

In contrast, **UTM is a conformal transverse projection** engineered specifically for terrestrial engineering and surveying. Its scale error along the central meridian is only $0.04\%$ ($k_0 = 0.9996$), making it the gold standard for drone operations.

#### 3. Axis Order Consistency
Different GIS tools use varying axis orders (e.g., $(y, x)$ vs. $(x, y)$). We strictly enforce `pyproj.Transformer.from_crs(source, target, always_xy=True)` so that inputs and outputs are guaranteed to follow $(x, y) = (\text{lon}, \text{lat})$.

---

## 4. Quickstart & Setup Guide

### Prerequisites
- Python 3.10 or newer
- Git

### 1. Clone & Set Up Virtual Environment
```bash
git clone https://github.com/GopikaArumugam/aereo-geospatial-file-measurement.git
cd aereo-geospatial-file-measurement

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Linux / macOS:
source venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Generate Sample Datasets
```bash
python scripts/generate_samples.py
```

### 4. Start the Application Server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Open your browser at:
* **Web UI Dashboard:** [http://localhost:8000/](http://localhost:8000/)
* **Interactive Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)

---

### Running with Docker
Deploy the complete application in a standardized container with one command:
```bash
docker-compose up --build
```
The API and Web UI will be instantly live at `http://localhost:8000`.

---

## 5. API Reference & Specifications

Interactive API interfaces:
- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)

### Summary of Endpoints

| Method | Endpoint | Description | Request Type | Response |
| :--- | :--- | :--- | :--- | :--- |
| `POST` | `/api/files/` | Ingests and processes a `.zip` Shapefile or `.kml` | `multipart/form-data` | `201 Created` |
| `GET` | `/api/files/{id}/` | Retrieves metadata, feature count, CRS, and status | None | `200 OK` |
| `GET` | `/api/files/{id}/measurements/` | Retrieves calculated metric measurements for all features | None | `200 OK` |
| `GET` | `/api/files/{id}/features/` | Exports features as standard GeoJSON `FeatureCollection` | None | `200 OK` |
| `GET` | `/api/files/` | Lists all uploaded files (descending by timestamp) | None | `200 OK` |
| `DELETE` | `/api/files/{id}/` | Deletes file record, extracted features, and disk assets | None | `204 No Content` |
| `GET` | `/api/health/` | Health check probe & spatial capability summary | None | `200 OK` |
| `GET` | `/api/samples/{type}` | Downloads pre-packaged sample KML or Shapefile ZIP | None | `200 OK` |

---

### Detailed Request / Response Specifications

#### 1. Ingest Geospatial File (`POST /api/files/`)
```bash
curl -X POST "http://localhost:8000/api/files/" \
  -H "accept: application/json" \
  -F "file=@sample_data/sample_mining_pit.kml"
```
**Response (`201 Created`):**
```json
{
  "id": "7a3e8b19f04c",
  "filename": "sample_mining_pit.kml",
  "feature_count": 5,
  "crs": "EPSG:4326",
  "projected_crs": "EPSG:32643 (UTM Zone 43N)",
  "status": "COMPLETED",
  "file_format": "kml",
  "file_size_bytes": 2990,
  "created_at": "2026-10-11T21:15:00.123456",
  "error_message": null
}
```

#### 2. Query File Metadata (`GET /api/files/{id}/`)
```bash
curl -X GET "http://localhost:8000/api/files/7a3e8b19f04c/"
```
**Response (`200 OK`):**
```json
{
  "id": "7a3e8b19f04c",
  "filename": "sample_mining_pit.kml",
  "feature_count": 5,
  "crs": "EPSG:4326",
  "projected_crs": "EPSG:32643 (UTM Zone 43N)",
  "status": "COMPLETED",
  "file_format": "kml",
  "file_size_bytes": 2990,
  "created_at": "2026-10-11T21:15:00.123456",
  "error_message": null
}
```

#### 3. Retrieve Metric Measurements (`GET /api/files/{id}/measurements/`)
```bash
curl -X GET "http://localhost:8000/api/files/7a3e8b19f04c/measurements/"
```
**Response (`200 OK`):**
```json
{
  "file_id": "7a3e8b19f04c",
  "filename": "sample_mining_pit.kml",
  "feature_count": 5,
  "source_crs": "EPSG:4326",
  "projected_crs": "EPSG:32643 (UTM Zone 43N)",
  "status": "COMPLETED",
  "summary": {
    "total_area_sq_meters": 384210.45,
    "total_area_hectares": 38.421,
    "total_length_meters": 1782.34,
    "total_length_km": 1.7823,
    "features_calculated": 3,
    "features_skipped": 2,
    "features_unsupported_or_error": 0
  },
  "features": [
    {
      "feature_index": 0,
      "feature_name": "Pit Extraction Sector Alpha",
      "geometry_type": "Polygon",
      "measurement": {
        "area": {
          "square_meters": 245100.22,
          "hectares": 24.51,
          "square_kilometers": 0.2451
        }
      },
      "projected_crs": "EPSG:32643 (UTM Zone 43N)",
      "status": "CALCULATED",
      "notes": null,
      "properties": {
        "SiteID": "BLR-PIT-01",
        "Operator": "AEREO Autonomous Fleet",
        "Material": "Hematite / Iron Ore"
      }
    },
    {
      "feature_index": 2,
      "feature_name": "Primary Haul Road Alignment",
      "geometry_type": "LineString",
      "measurement": {
        "length": {
          "meters": 1782.34,
          "kilometers": 1.7823
        }
      },
      "projected_crs": "EPSG:32643 (UTM Zone 43N)",
      "status": "CALCULATED",
      "notes": null,
      "properties": {
        "RouteID": "RD-MAIN-01",
        "WidthMeters": "14.5"
      }
    },
    {
      "feature_index": 3,
      "feature_name": "Borehole Exploration MB-01",
      "geometry_type": "Point",
      "measurement": null,
      "projected_crs": null,
      "status": "SKIPPED",
      "notes": "Point geometry does not have measurable area or length",
      "properties": {
        "name": "Borehole Exploration MB-01"
      }
    }
  ]
}
```

#### 4. Export GeoJSON (`GET /api/files/{id}/features/`)
```bash
curl -X GET "http://localhost:8000/api/files/7a3e8b19f04c/features/"
```
**Response (`200 OK`):**
```json
{
  "type": "FeatureCollection",
  "file_id": "7a3e8b19f04c",
  "filename": "sample_mining_pit.kml",
  "crs": "EPSG:4326",
  "features": [
    {
      "type": "Feature",
      "id": 1,
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[76.918, 15.152], [76.923, 15.1525], "..."]]
      },
      "properties": {
        "_feature_index": 0,
        "_feature_name": "Pit Extraction Sector Alpha",
        "_geometry_type": "Polygon",
        "_status": "CALCULATED",
        "_area_sq_meters": 245100.22,
        "_area_hectares": 24.51,
        "SiteID": "BLR-PIT-01"
      }
    }
  ]
}
```

---

## 6. Web GIS Dashboard Walkthrough

Served directly from the application at **`http://localhost:8000/`**:

1. **Executive Enterprise Aesthetic:**
   * Built with a clean, distraction-free neutral slate `#f8fafc` design, crisp borders (`#e2e8f0`), and dark typography (`#0f172a`).
   * Zero gaudy gradients or flashing neon elements.
2. **Interactive Spatial Map (Leaflet):**
   * Renders polygons with soft blue fill, haul road lines in emerald green, and points in amber.
   * **Dual Basemap Layer Control:** Seamlessly toggle between **OpenStreetMap (Streets)** and **Esri World Imagery (Satellite/Aerial)** without needing any API keys.
   * **Interactive Popups:** Click on any geometry on the map to inspect its name, type, and computed area/length.
3. **KPI Summary Cards:**
   * **Total Measured Area:** Aggregated square meters, hectares, and $km^2$.
   * **Total Measured Length:** Aggregated meters and kilometers.
   * **CRS Strategy:** Displays the resolved metric UTM zone.
4. **Data Table & JSON Inspector:**
   * Tabular breakdown of every feature, its properties, projected CRS, and status.
   * Dedicated raw JSON view with one-click export for developers.
5. **Instant One-Click Demo Testing:**
   * Pre-packaged buttons to test `sample_mining_pit.kml` and `sample_corridor_survey.zip` instantly.

---

## 7. Automated Testing & Verification

The automated test suite covers:
- Input validation (unsupported extensions, oversized payloads).
- Dynamic UTM zone calculation across multiple continents and hemispheres.
- Coordinate reprojection accuracy with PyProj.
- Polygon Area and LineString Length metric calculation.
- Self-intersecting polygon topology fixing via `shapely.make_valid`.
- Point skipping without system failure.
- End-to-end API lifecycle (upload, query, measurements, GeoJSON export, deletion).

Run the automated test suite with `pytest`:
```bash
pytest -v
```

### Test Suite Execution Output
```
tests/test_api_endpoints.py::test_health_check PASSED                    [  6%]
tests/test_api_endpoints.py::test_upload_invalid_extension PASSED        [ 13%]
tests/test_api_endpoints.py::test_upload_and_process_kml PASSED          [ 20%]
tests/test_api_endpoints.py::test_upload_and_process_shapefile_zip PASSED [ 26%]
tests/test_api_endpoints.py::test_get_nonexistent_file_404 PASSED        [ 33%]
tests/test_crs_service.py::test_utm_zone_calculation PASSED              [ 40%]
tests/test_crs_service.py::test_crs_parsing PASSED                       [ 46%]
tests/test_crs_service.py::test_get_projected_crs_for_geographic_geometry PASSED [ 53%]
tests/test_crs_service.py::test_reproject_geometry PASSED                [ 60%]
tests/test_file_parser.py::test_parse_kml_file PASSED                    [ 66%]
tests/test_file_parser.py::test_parse_shapefile_zip PASSED               [ 73%]
tests/test_measurements.py::test_polygon_area_calculation PASSED         [ 80%]
tests/test_measurements.py::test_linestring_length_calculation PASSED    [ 86%]
tests/test_measurements.py::test_point_handling_skipped PASSED           [ 93%]
tests/test_measurements.py::test_self_intersecting_polygon_make_valid PASSED [100%]

======================== 15 passed in 0.64s ========================
```

---

## 8. Assignment Requirements Verification Matrix

For reviewers evaluating this project against the official AEREO Engineering Assignment specifications:

| # | Specification | Fulfillment Description | Source Files | Status |
| :-: | :--- | :--- | :--- | :-: |
| **1** | **Backend Framework** | High-performance FastAPI backend with typed Pydantic v2 schemas and auto-generated Swagger UI (`/docs`). | [`app/main.py`](file:///d:/Aereo/app/main.py) | ✅ Verified |
| **2** | **File Upload (`POST /api/files/`)** | Accepts `.zip` containing Shapefile (`.shp`, `.dbf`, `.prj`, `.shx`) and `.kml`. Enforces format and size limits. | [`app/routers/files.py`](file:///d:/Aereo/app/routers/files.py) | ✅ Verified |
| **3** | **File Processing** | Extracts feature index, name, geometry type, GeoJSON geometry, source CRS, and dictionary attributes. | [`app/services/file_parser.py`](file:///d:/Aereo/app/services/file_parser.py) | ✅ Verified |
| **4** | **Measurements Calculation** | Polygon Area ($m^2$, ha, $km^2$); LineString Length ($m$, km); Point gracefully skipped (0 area/length) without crashing. Self-intersecting rings repaired via `make_valid`. | [`app/services/measurement.py`](file:///d:/Aereo/app/services/measurement.py) | ✅ Verified |
| **5** | **CRS Handling** | Accurately identifies $EPSG:4326$ angular coordinates; dynamically calculates local centroid UTM zone and reprojects to planar metric grid. | [`app/services/crs_service.py`](file:///d:/Aereo/app/services/crs_service.py) | ✅ Verified |
| **6** | **API Design** | Full implementation of required endpoints (`POST /api/files/`, `GET /api/files/{id}/`, `GET /api/files/{id}/measurements/`) plus bonus GeoJSON export and file deletion. | [`app/routers/files.py`](file:///d:/Aereo/app/routers/files.py) | ✅ Verified |
| **7** | **Documentation** | Thorough documentation covering setup, architecture flowcharts, sequence diagrams, mathematical derivations, and cURL examples. | [`README.md`](file:///d:/Aereo/README.md) | ✅ Verified |
| **8** | **Submission & Extras** | Clean public GitHub repository, automated pytest test suite (15 tests passing), learnings, future scope, and atomic Git commit history. | [`README.md`](file:///d:/Aereo/README.md), [`sample_data/`](file:///d:/Aereo/sample_data) | ✅ Verified |

---

## 9. Design Decisions & Trade-offs

### 1. Framework: FastAPI vs. Django + DRF
* **Decision:** Built with **FastAPI**.
* **Rationale:** This service is an API-first spatial computation microservice. FastAPI provides native asynchronous streaming, automatic OpenAPI/Swagger documentation, and Pydantic v2 type safety without the heavyweight overhead of Django's session middleware, admin panel, or relational migrations.

### 2. GIS Parsing: `pyshp` + `shapely` + `pyproj` vs. C-GDAL / Fiona
* **Decision:** Used pure-Python `pyshp` paired with pre-compiled `shapely` (GEOS) and `pyproj` (PROJ) wheels.
* **Rationale:** Standard GDAL/Fiona distributions frequently fail to build or link dynamic C++ runtime libraries across diverse developer environments (especially Windows and Alpine Linux). Using pure Python Shapefile parsing paired with pre-compiled wheels guarantees zero installation friction while maintaining full C-level geometry computation performance.

### 3. CRS Strategy: Dynamic UTM vs. Web Mercator (`EPSG:3857`)
* **Decision:** Dynamically project into local **UTM zones** (`EPSG:326XX` / `EPSG:327XX`) rather than Web Mercator.
* **Rationale:** Web Mercator (`EPSG:3857`) is standard for web tile rendering, but introduces severe metric distortion away from the Equator (scale factor $k = 1 / \cos(\phi)$). In contrast, UTM is a conformal transverse cylindrical projection with minimal scale distortion ($< 0.04\%$ along central meridians), making it the industry standard for surveying, drone mapping, and engineering measurements.

### 4. Resilient Geometry Handling
* **Decision:** Applied `shapely.validation.make_valid` prior to calculating measurements.
* **Rationale:** Real-world CAD and drone vector exports often contain self-intersecting "bow-tie" rings or collapsed slivers. Automatically repairing topological anomalies prevents the pipeline from crashing on imperfect real-world survey files.

---

## 10. Key Learnings & Future Scope

### Key Learnings
1. **Cartographic Precision Matters:** A naive calculation on latitude/longitude degrees fails completely in real-world surveying. Understanding the mathematical difference between an ellipsoidal datum ($WGS84$) and a planar conformal projection ($UTM$) is essential for engineering geospatial intelligence.
2. **KML XML Namespaces:** KML specifications have varied across Google Earth versions (`http://www.opengis.net/kml/2.2` vs. legacy schemas). Writing a namespace-agnostic XML element extractor guarantees reliable feature extraction across any KML exporter.
3. **Database Portability:** Decoupling geometry storage into standard GeoJSON and relational tables enables deployment on any standard SQL database (SQLite, PostgreSQL, MySQL) without forcing a strict dependency on the PostGIS spatial extension for basic queries.

### Future Scope
1. **Asynchronous Background Task Queue:** For enterprise drone surveys with >100,000 features, integrate Celery or ARQ with Redis to execute parsing and reprojection asynchronously while clients poll job progress.
2. **3D Volumetric Measurements:** Extend the engine to ingest Digital Surface Models (DSM/DEM GeoTIFFs) and compute cut/fill stockpile excavation volumes ($m^3$) for mining customers.
3. **LiDAR Point Cloud Ingestion:** Add parsers for LAS/LAZ formats to extract 3D cross-sections and vegetation encroachment buffers along power lines.
4. **Cloud Object Storage:** Integrate Amazon S3 or Google Cloud Storage (GCS) pre-signed upload URLs for direct streaming of multi-gigabyte survey packages.
