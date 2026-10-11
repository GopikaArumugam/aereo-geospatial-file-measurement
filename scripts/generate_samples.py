from pathlib import Path
import zipfile
import shapefile

def create_sample_kml(output_path: Path):
    kml_content = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <name>Ballari Mining Pit Drone Survey</name>
    <description>AEREO Aerial Survey Dataset - Mining Extraction Pit, Haul Roads, and Boreholes</description>
    
    <!-- Feature 1: Mining Excavation Pit (Polygon) -->
    <Placemark>
      <name>Pit Extraction Sector Alpha</name>
      <description>Active iron ore excavation zone</description>
      <ExtendedData>
        <Data name="SiteID"><value>BLR-PIT-01</value></Data>
        <Data name="Operator"><value>AEREO Autonomous Fleet</value></Data>
        <Data name="Material"><value>Hematite / Iron Ore</value></Data>
      </ExtendedData>
      <Polygon>
        <extrude>1</extrude>
        <altitudeMode>relativeToGround</altitudeMode>
        <outerBoundaryIs>
          <LinearRing>
            <coordinates>
              76.9180,15.1520,0 76.9230,15.1525,0 76.9240,15.1480,0 76.9200,15.1460,0 76.9170,15.1490,0 76.9180,15.1520,0
            </coordinates>
          </LinearRing>
        </outerBoundaryIs>
      </Polygon>
    </Placemark>

    <!-- Feature 2: Overburden Stockpile Dump (Polygon) -->
    <Placemark>
      <name>Overburden Stockpile OB-North</name>
      <description>Designated non-mineral dump site</description>
      <ExtendedData>
        <Data name="SiteID"><value>BLR-OB-02</value></Data>
        <Data name="CapacityPct"><value>68%</value></Data>
      </ExtendedData>
      <Polygon>
        <outerBoundaryIs>
          <LinearRing>
            <coordinates>
              76.9250,15.1530,0 76.9285,15.1535,0 76.9290,15.1495,0 76.9255,15.1490,0 76.9250,15.1530,0
            </coordinates>
          </LinearRing>
        </outerBoundaryIs>
      </Polygon>
    </Placemark>

    <!-- Feature 3: Main Haul Road Corridor (LineString) -->
    <Placemark>
      <name>Primary Haul Road Alignment</name>
      <description>Heavy dumper truck transit road from pit to crusher</description>
      <ExtendedData>
        <Data name="RouteID"><value>RD-MAIN-01</value></Data>
        <Data name="WidthMeters"><value>14.5</value></Data>
      </ExtendedData>
      <LineString>
        <coordinates>
          76.9150,15.1500,0 76.9170,15.1490,0 76.9200,15.1460,0 76.9250,15.1450,0 76.9290,15.1440,0
        </coordinates>
      </LineString>
    </Placemark>

    <!-- Feature 4: Geological Borehole (Point) -->
    <Placemark>
      <name>Borehole Exploration MB-01</name>
      <description>Core sample monitoring point</description>
      <Point>
        <coordinates>76.9195,15.1495,0</coordinates>
      </Point>
    </Placemark>

    <!-- Feature 5: Drone Launch Base (Point) -->
    <Placemark>
      <name>GCS Drone Launch Pad</name>
      <description>Survey ground control station</description>
      <Point>
        <coordinates>76.9140,15.1510,0</coordinates>
      </Point>
    </Placemark>

  </Document>
</kml>
"""
    output_path.write_text(kml_content, encoding="utf-8")
    print(f"Created {output_path}")


def create_sample_shapefile_zip(output_zip: Path):
    temp_dir = output_zip.parent / "temp_shp_build"
    temp_dir.mkdir(parents=True, exist_ok=True)
    base_name = temp_dir / "corridor_survey"

    # Create Polygon Shapefile with pyshp
    w = shapefile.Writer(str(base_name), shapeType=shapefile.POLYGON)
    w.field("NAME", "C", size=50)
    w.field("ZONE_TYPE", "C", size=30)
    w.field("PRIORITY", "N", size=5)

    # Polygon 1: Solar Array Boundary
    w.poly([
        [[77.5800, 12.9700], [77.5850, 12.9705], [77.5845, 12.9660], [77.5795, 12.9655], [77.5800, 12.9700]]
    ])
    w.record("Solar Farm Block A", "Renewable Energy", 1)

    # Polygon 2: Substation Boundary
    w.poly([
        [[77.5860, 12.9710], [77.5890, 12.9712], [77.5888, 12.9680], [77.5858, 12.9678], [77.5860, 12.9710]]
    ])
    w.record("Grid Substation 400kV", "Utility Infrastructure", 1)

    w.close()

    # Create WGS84 .prj file
    prj_content = 'GEOGCS["GCS_WGS_1984",DATUM["D_WGS_1984",SPHEROID["WGS_1984",6378137.0,298.257223563]],PRIMEM["Greenwich",0.0],UNIT["Degree",0.0174532925199433]]'
    (temp_dir / "corridor_survey.prj").write_text(prj_content, encoding="utf-8")

    # Zip all shapefile parts
    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as z:
        for ext in [".shp", ".shx", ".dbf", ".prj"]:
            file_to_add = temp_dir / f"corridor_survey{ext}"
            if file_to_add.exists():
                z.write(file_to_add, arcname=f"corridor_survey{ext}")
                file_to_add.unlink()

    temp_dir.rmdir()
    print(f"Created {output_zip}")


if __name__ == "__main__":
    samples_dir = Path("sample_data")
    samples_dir.mkdir(parents=True, exist_ok=True)
    create_sample_kml(samples_dir / "sample_mining_pit.kml")
    create_sample_shapefile_zip(samples_dir / "sample_corridor_survey.zip")
