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
import threading

app = FastAPI(title="Contours Bureaux de Vote API")

# Scaleway Object Storage URL for direct remote reading
PARQUET_URL = "https://contours-bureaux-vote.s3.fr-par.scw.cloud/20251108_contours_bureaux_vote.parquet"

# Initialize DuckDB connection - use read_only and shared connection
print(f"Initializing DuckDB with remote parquet file from {PARQUET_URL}...")

# Use a persistent database file to allow concurrent reads
# This is safer than :memory: for concurrent access
import tempfile
import os
db_path = os.path.join(tempfile.gettempdir(), 'contours_bdv.duckdb')

# Create the database with the view
conn = duckdb.connect(database=db_path)

try:
    # Install and load extensions for remote file access and spatial operations
    print("Installing extensions...")
    conn.execute("INSTALL httpfs;")
    conn.execute("INSTALL spatial;")
    print("Loading extensions...")
    conn.execute("LOAD httpfs;")
    conn.execute("LOAD spatial;")

    # Drop view if exists and recreate
    print("Creating view from remote parquet file...")
    conn.execute("DROP VIEW IF EXISTS contours;")
    conn.execute(f"""
        CREATE VIEW contours AS
        SELECT * FROM read_parquet('{PARQUET_URL}')
    """)

    print(f"✓ DuckDB initialized with remote parquet file")
    print(f"✓ Data will be queried directly from Scaleway Object Storage")
    print(f"✓ Spatial extension loaded for fast GeoJSON conversion")
    print(f"✓ Database file: {db_path}")
except Exception as e:
    print(f"ERROR: Failed to initialize DuckDB with remote file: {e}")
    print("This may be due to httpfs extension installation issues or network problems.")
    import sys
    sys.exit(1)
finally:
    # Close the initialization connection
    conn.close()

# Function to get a connection (each request will get its own)
def get_db_connection():
    """Get a read-only connection to the database"""
    conn = duckdb.connect(database=db_path, read_only=True)
    conn.execute("LOAD httpfs;")
    conn.execute("LOAD spatial;")
    return conn


# Cache for search results - loaded once at startup
SEARCH_CACHE = {
    "departements": [],
    "circonscriptions": [],
    "communes": []
}

def load_search_cache():
    """Load all searchable entities into memory cache at startup"""
    print("Loading search cache...")
    import time
    start = time.time()

    with get_db_connection() as conn:
        # Load departments
        dept_query = """
            SELECT DISTINCT
                codeDepartement as code,
                nomDepartement as name
            FROM contours
            ORDER BY nomDepartement
        """
        SEARCH_CACHE["departements"] = conn.execute(dept_query).fetchdf().to_dict('records')

        # Load circonscriptions
        circ_query = """
            SELECT DISTINCT
                nomCirconscription as name,
                nomDepartement as departement
            FROM contours
            ORDER BY nomCirconscription
        """
        SEARCH_CACHE["circonscriptions"] = conn.execute(circ_query).fetchdf().to_dict('records')

        # Load communes
        commune_query = """
            SELECT DISTINCT
                codeCommune as code,
                nomCommune as name,
                nomDepartement as departement
            FROM contours
            ORDER BY nomCommune
        """
        SEARCH_CACHE["communes"] = conn.execute(commune_query).fetchdf().to_dict('records')

    elapsed = time.time() - start
    print(f"✓ Search cache loaded in {elapsed:.2f}s")
    print(f"  - {len(SEARCH_CACHE['departements'])} departments")
    print(f"  - {len(SEARCH_CACHE['circonscriptions'])} circonscriptions")
    print(f"  - {len(SEARCH_CACHE['communes'])} communes")

# Load cache at startup
load_search_cache()


def df_to_geojson_duckdb(conn, query, params, max_features=50000):
    """
    Convert query results to GeoJSON using DuckDB's ST_AsGeoJSON.
    Much faster than GeoPandas conversion.

    Args:
        conn: DuckDB connection
        query: SQL query that returns geometry column
        params: Query parameters
        max_features: Maximum number of features to prevent memory issues
    """
    import time
    start = time.time()

    # First check count
    count_query = f"SELECT COUNT(*) FROM ({query})"
    count = conn.execute(count_query, params).fetchone()[0]

    if count > max_features:
        raise ValueError(f"Too many features ({count}). Maximum allowed: {max_features}")

    print(f"Building GeoJSON for {count} features using DuckDB...")

    # Build GeoJSON directly in DuckDB using ST_AsGeoJSON
    # This creates a proper FeatureCollection
    geojson_query = f"""
    SELECT json_object(
        'type', 'FeatureCollection',
        'features', json_group_array(
            json_object(
                'type', 'Feature',
                'properties', json_object(
                    'codeBureauVote', codeBureauVote,
                    'numeroBureauVote', numeroBureauVote,
                    'codeCommune', codeCommune,
                    'nomCommune', nomCommune,
                    'codeDepartement', codeDepartement,
                    'nomDepartement', nomDepartement,
                    'nomCirconscription', nomCirconscription
                ),
                'geometry', json(ST_AsGeoJSON(geometry))
            )
        )
    ) as geojson
    FROM ({query})
    """

    result = conn.execute(geojson_query, params).fetchone()[0]

    elapsed = time.time() - start
    print(f"✓ GeoJSON built in {elapsed:.2f}s")

    return result


@app.get("/api")
def read_root():
    """API info"""
    return {
        "name": "Contours Bureaux de Vote API",
        "endpoints": {
            "/search": "Search departments, circonscriptions, or communes",
            "/download/departement/{code}": "Download GeoJSON for a department",
            "/download/circonscription/{department}/{name}": "Download GeoJSON for a circonscription",
            "/download/commune/{code}": "Download GeoJSON for a commune",
            "/api/info": "Get dataset information"
        }
    }


@app.get("/api/info")
def get_data_info():
    """Get information about the dataset"""
    # Extract date from filename (format: YYYYMMDD_contours_bureaux_vote.parquet)
    import re
    date_match = re.search(r'(\d{4})(\d{2})(\d{2})_', PARQUET_URL)

    if date_match:
        year, month, day = date_match.groups()
        last_updated = f"{day}/{month}/{year}"
    else:
        last_updated = "Non disponible"

    return {
        "last_updated": last_updated,
        "source": "data.gouv.fr",
        "source_url": "https://www.data.gouv.fr/fr/datasets/proposition-de-contours-des-bureaux-de-vote/",
        "method": "Diagrammes de Voronoi"
    }


def remove_accents(text: str) -> str:
    """Remove accents from text for accent-insensitive search"""
    import unicodedata
    return ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    )


@app.get("/search")
def search(q: str = "", type: str = "all"):
    """
    Search for departments, circonscriptions, or communes.
    Uses in-memory cache for instant results.

    Args:
        q: Search query
        type: Filter by type (departement, circonscription, commune, all)
    """
    import time
    start = time.time()

    results = {"departements": [], "circonscriptions": [], "communes": []}

    if not q:
        return results

    query_lower = q.lower()
    query_normalized = remove_accents(query_lower)

    # Search departments from cache
    if type in ["all", "departement"]:
        matches = []
        for dept in SEARCH_CACHE["departements"]:
            name_normalized = remove_accents(dept['name'].lower())
            code_lower = dept['code'].lower()
            if query_normalized in name_normalized or query_lower in code_lower:
                matches.append(dept)
                if len(matches) >= 10:
                    break
        results["departements"] = matches

    # Search circonscriptions from cache
    if type in ["all", "circonscription"]:
        matches = []
        for circ in SEARCH_CACHE["circonscriptions"]:
            name_normalized = remove_accents(circ['name'].lower())
            dept_normalized = remove_accents(circ['departement'].lower())
            if query_normalized in name_normalized or query_normalized in dept_normalized:
                matches.append(circ)
                if len(matches) >= 10:
                    break
        results["circonscriptions"] = matches

    # Search communes from cache
    if type in ["all", "commune"]:
        matches = []
        for commune in SEARCH_CACHE["communes"]:
            name_normalized = remove_accents(commune['name'].lower())
            code_lower = commune['code'].lower()
            if query_normalized in name_normalized or query_lower in code_lower:
                matches.append(commune)
                if len(matches) >= 10:
                    break
        results["communes"] = matches

    elapsed = time.time() - start
    print(f"Search for '{q}' completed in {elapsed:.3f}s ({len(results['departements'])} depts, {len(results['circonscriptions'])} circs, {len(results['communes'])} communes)")

    return results


@app.get("/download/departement/{code}")
def download_departement(code: str):
    """Download GeoJSON for a specific department"""

    print(f"Received department download request for: '{code}'")

    query = """
        SELECT * FROM contours
        WHERE codeDepartement = ?
    """

    try:
        with get_db_connection() as conn:
            geojson_str = df_to_geojson_duckdb(conn, query, [code])
    except ValueError as e:
        raise HTTPException(
            status_code=413,
            detail=f"Dataset too large to download. Please contact support for bulk data access."
        )

    return Response(
        content=geojson_str,
        media_type="application/geo+json",
        headers={"Content-Disposition": f"attachment; filename=departement_{code}.geojson"}
    )


@app.get("/download/circonscription/{department}/{name}")
def download_circonscription(department: str, name: str):
    """Download GeoJSON for a specific circonscription"""
    import unicodedata

    # Normalize the input to NFC form
    name_normalized = unicodedata.normalize('NFC', name)

    # Debug logging
    print(f"Received circonscription download request for: '{name}'")
    print(f"Normalized to: '{name_normalized}'")
    print(f"Input bytes: {name.encode('utf-8')}")
    print(f"Normalized bytes: {name_normalized.encode('utf-8')}")

    # Try exact match first with department filter
    query = """
        SELECT * FROM contours
        WHERE nomCirconscription = ? AND nomDepartement = ?
    """

    try:
        with get_db_connection() as conn:
            geojson_str = df_to_geojson_duckdb(conn, query, [name_normalized, department])
    except ValueError as e:
        # Check if it's a "too many features" error or "no results" error
        if "Too many features" in str(e):
            raise HTTPException(
                status_code=413,
                detail=str(e) + " Please contact support for bulk data access."
            )
        # Try case-insensitive match
        case_insensitive_query = """
            SELECT * FROM contours
            WHERE LOWER(nomCirconscription) = LOWER(?) AND LOWER(nomDepartement) = LOWER(?)
        """
        try:
            with get_db_connection() as conn:
                geojson_str = df_to_geojson_duckdb(conn, case_insensitive_query, [name_normalized, department])
            print(f"Found match with case-insensitive search")
        except:
            raise HTTPException(
                status_code=404,
                detail=f"Circonscription '{name}' not found in department '{department}'"
            )

    # Create safe filename
    safe_dept = department.replace(" ", "_").replace("/", "-")
    safe_name = name.replace(" ", "_").replace("/", "-")

    return Response(
        content=geojson_str,
        media_type="application/geo+json",
        headers={"Content-Disposition": f"attachment; filename=circonscription_{safe_dept}_{safe_name}.geojson"}
    )


@app.get("/download/commune/{code}")
def download_commune(code: str):
    """Download GeoJSON for a specific commune"""

    print(f"Received commune download request for: '{code}'")

    query = """
        SELECT * FROM contours
        WHERE codeCommune = ?
    """

    try:
        with get_db_connection() as conn:
            geojson_str = df_to_geojson_duckdb(conn, query, [code])
    except ValueError as e:
        raise HTTPException(
            status_code=413,
            detail=f"Dataset too large to download. Please contact support for bulk data access."
        )

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
