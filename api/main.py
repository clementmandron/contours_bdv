"""
FastAPI backend for voting district contours.
Uses DuckDB for fast querying with minimal memory.
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse, Response
from pathlib import Path
import duckdb
from typing import List, Dict
import geopandas as gpd
from shapely import wkb
import json

app = FastAPI(title="Contours Bureaux de Vote API")

# Scaleway Object Storage URL for direct remote reading
PARQUET_URL = "https://contours-bureaux-vote.s3.fr-par.scw.cloud/20251108_contours_bureaux_vote.parquet"

# Initialize DuckDB connection
print(f"Initializing DuckDB with remote parquet file from {PARQUET_URL}...")
conn = duckdb.connect(database=':memory:')

# Install and load httpfs extension for remote file access
conn.execute("INSTALL httpfs;")
conn.execute("LOAD httpfs;")

# Create view that reads directly from remote parquet file
# Using a view instead of a table to avoid loading all data into memory
conn.execute(f"""
    CREATE VIEW contours AS
    SELECT * FROM read_parquet('{PARQUET_URL}')
""")

print(f"✓ DuckDB initialized with remote parquet file")
print(f"✓ Data will be queried directly from Scaleway Object Storage")


def df_to_geojson(df):
    """Convert DuckDB dataframe to GeoJSON string"""
    # Convert WKB geometry column to shapely geometries
    df['geometry'] = df['geometry'].apply(lambda x: wkb.loads(bytes(x)))
    # Create GeoDataFrame
    gdf = gpd.GeoDataFrame(df, geometry='geometry')
    # Convert to GeoJSON
    return gdf.to_json()


@app.get("/api")
def read_root():
    """API info"""
    return {
        "name": "Contours Bureaux de Vote API",
        "endpoints": {
            "/search": "Search departments, circonscriptions, or communes",
            "/download/{type}/{name}": "Download GeoJSON for a specific area"
        }
    }


@app.get("/search")
def search(q: str = "", type: str = "all"):
    """
    Search for departments, circonscriptions, or communes.

    Args:
        q: Search query
        type: Filter by type (departement, circonscription, commune, all)
    """

    results = {"departements": [], "circonscriptions": [], "communes": []}

    if not q:
        return results

    query_lower = q.lower()

    # Search departments
    if type in ["all", "departement"]:
        dept_query = f"""
            SELECT DISTINCT
                codeDepartement as code,
                nomDepartement as name
            FROM contours
            WHERE LOWER(nomDepartement) LIKE '%{query_lower}%'
               OR codeDepartement LIKE '%{query_lower}%'
            ORDER BY nomDepartement
            LIMIT 10
        """
        results["departements"] = conn.execute(dept_query).fetchdf().to_dict('records')

    # Search circonscriptions
    if type in ["all", "circonscription"]:
        circ_query = f"""
            SELECT DISTINCT
                nomCirconscription as name,
                nomDepartement as departement
            FROM contours
            WHERE LOWER(nomCirconscription) LIKE '%{query_lower}%'
            ORDER BY nomCirconscription
            LIMIT 10
        """
        results["circonscriptions"] = conn.execute(circ_query).fetchdf().to_dict('records')

    # Search communes
    if type in ["all", "commune"]:
        commune_query = f"""
            SELECT DISTINCT
                codeCommune as code,
                nomCommune as name,
                nomDepartement as departement
            FROM contours
            WHERE LOWER(nomCommune) LIKE '%{query_lower}%'
               OR codeCommune LIKE '%{query_lower}%'
            ORDER BY nomCommune
            LIMIT 10
        """
        results["communes"] = conn.execute(commune_query).fetchdf().to_dict('records')

    return results


@app.get("/download/departement/{code}")
def download_departement(code: str):
    """Download GeoJSON for a specific department"""

    query = f"""
        SELECT * FROM contours
        WHERE codeDepartement = '{code}'
    """

    df = conn.execute(query).fetchdf()

    if len(df) == 0:
        raise HTTPException(status_code=404, detail="Department not found")

    geojson_str = df_to_geojson(df)

    return Response(
        content=geojson_str,
        media_type="application/geo+json",
        headers={"Content-Disposition": f"attachment; filename=departement_{code}.geojson"}
    )


@app.get("/download/circonscription/{name}")
def download_circonscription(name: str):
    """Download GeoJSON for a specific circonscription"""

    query = f"""
        SELECT * FROM contours
        WHERE nomCirconscription = '{name.replace("'", "''")}'
    """

    df = conn.execute(query).fetchdf()

    if len(df) == 0:
        raise HTTPException(status_code=404, detail="Circonscription not found")

    geojson_str = df_to_geojson(df)

    return Response(
        content=geojson_str,
        media_type="application/geo+json",
        headers={"Content-Disposition": f"attachment; filename=circonscription_{name}.geojson"}
    )


@app.get("/download/commune/{code}")
def download_commune(code: str):
    """Download GeoJSON for a specific commune"""

    query = f"""
        SELECT * FROM contours
        WHERE codeCommune = '{code}'
    """

    df = conn.execute(query).fetchdf()

    if len(df) == 0:
        raise HTTPException(status_code=404, detail="Commune not found")

    geojson_str = df_to_geojson(df)

    return Response(
        content=geojson_str,
        media_type="application/geo+json",
        headers={"Content-Disposition": f"attachment; filename=commune_{code}.geojson"}
    )


# Root route - serve the frontend
@app.get("/")
def serve_app():
    """Serve the frontend"""
    return FileResponse("static/index.html")

# Serve static files (frontend)
app.mount("/static", StaticFiles(directory="static"), name="static")
