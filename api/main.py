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

try:
    # Install and load httpfs extension for remote file access
    print("Installing httpfs extension...")
    conn.execute("INSTALL httpfs;")
    print("Loading httpfs extension...")
    conn.execute("LOAD httpfs;")

    # Create view that reads directly from remote parquet file
    # Using a view instead of a table to avoid loading all data into memory
    print("Creating view from remote parquet file...")
    conn.execute(f"""
        CREATE VIEW contours AS
        SELECT * FROM read_parquet('{PARQUET_URL}')
    """)

    print(f"✓ DuckDB initialized with remote parquet file")
    print(f"✓ Data will be queried directly from Scaleway Object Storage")
except Exception as e:
    print(f"ERROR: Failed to initialize DuckDB with remote file: {e}")
    print("This may be due to httpfs extension installation issues or network problems.")
    import sys
    sys.exit(1)


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
            "/download/{type}/{name}": "Download GeoJSON for a specific area",
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
    Search is accent-insensitive (e.g., 'fleville' will match 'Fléville').

    Args:
        q: Search query
        type: Filter by type (departement, circonscription, commune, all)
    """

    results = {"departements": [], "circonscriptions": [], "communes": []}

    if not q:
        return results

    query_lower = q.lower()
    query_normalized = remove_accents(query_lower)

    # Search departments
    if type in ["all", "departement"]:
        # Get all departments and filter in Python for accent-insensitive search
        dept_query = """
            SELECT DISTINCT
                codeDepartement as code,
                nomDepartement as name
            FROM contours
            ORDER BY nomDepartement
        """
        df = conn.execute(dept_query).fetchdf()

        # Filter with accent-insensitive matching
        filtered = df[
            df['name'].apply(lambda x: query_normalized in remove_accents(x.lower())) |
            df['code'].apply(lambda x: query_lower in x.lower())
        ]
        results["departements"] = filtered.head(10).to_dict('records')

    # Search circonscriptions
    if type in ["all", "circonscription"]:
        # Get all circonscriptions and filter in Python for accent-insensitive search
        circ_query = """
            SELECT DISTINCT
                nomCirconscription as name,
                nomDepartement as departement
            FROM contours
            ORDER BY nomCirconscription
        """
        df = conn.execute(circ_query).fetchdf()

        # Filter with accent-insensitive matching
        filtered = df[
            df['name'].apply(lambda x: query_normalized in remove_accents(x.lower())) |
            df['departement'].apply(lambda x: query_normalized in remove_accents(x.lower()))
        ]
        results["circonscriptions"] = filtered.head(10).to_dict('records')

    # Search communes
    if type in ["all", "commune"]:
        # For communes, get broader initial results then filter in Python
        # Use first few characters to limit initial dataset
        first_chars = query_normalized[:2] if len(query_normalized) >= 2 else query_normalized[0] if query_normalized else ''

        commune_query = f"""
            SELECT DISTINCT
                codeCommune as code,
                nomCommune as name,
                nomDepartement as departement
            FROM contours
            WHERE LOWER(nomCommune) LIKE '{first_chars}%'
               OR codeCommune LIKE '%{query_lower}%'
            ORDER BY nomCommune
            LIMIT 2000
        """
        df = conn.execute(commune_query).fetchdf()

        # Filter with accent-insensitive matching
        if not df.empty:
            filtered = df[
                df['name'].apply(lambda x: query_normalized in remove_accents(x.lower())) |
                df['code'].apply(lambda x: query_lower in x.lower())
            ]
            results["communes"] = filtered.head(10).to_dict('records')
        else:
            results["communes"] = []

    return results


@app.get("/download/departement/{code}")
def download_departement(code: str):
    """Download GeoJSON for a specific department"""

    print(f"Received department download request for: '{code}'")

    query = """
        SELECT * FROM contours
        WHERE codeDepartement = ?
    """

    df = conn.execute(query, [code]).fetchdf()

    if len(df) == 0:
        raise HTTPException(status_code=404, detail=f"Department not found: '{code}'")

    geojson_str = df_to_geojson(df)

    return Response(
        content=geojson_str,
        media_type="application/geo+json",
        headers={"Content-Disposition": f"attachment; filename=departement_{code}.geojson"}
    )


@app.get("/download/circonscription/{name}")
def download_circonscription(name: str):
    """Download GeoJSON for a specific circonscription"""
    import unicodedata

    # Normalize the input to NFC form
    name_normalized = unicodedata.normalize('NFC', name)

    # Debug logging
    print(f"Received circonscription download request for: '{name}'")
    print(f"Normalized to: '{name_normalized}'")
    print(f"Input bytes: {name.encode('utf-8')}")
    print(f"Normalized bytes: {name_normalized.encode('utf-8')}")

    # Try exact match first
    query = """
        SELECT * FROM contours
        WHERE nomCirconscription = ?
    """

    df = conn.execute(query, [name_normalized]).fetchdf()

    print(f"Query returned {len(df)} results")

    if len(df) == 0:
        # If exact match fails, try to find with accent-insensitive search
        # Get all circonscriptions and match in Python
        all_circs_query = """
            SELECT DISTINCT nomCirconscription
            FROM contours
        """
        all_circs = conn.execute(all_circs_query).fetchdf()

        # Normalize and compare
        name_no_accents = remove_accents(name_normalized.lower())
        matches = []
        for circ_name in all_circs['nomCirconscription']:
            circ_normalized = unicodedata.normalize('NFC', circ_name)
            if remove_accents(circ_normalized.lower()) == name_no_accents:
                matches.append(circ_normalized)

        if matches:
            print(f"Found match with accent-insensitive search: {matches[0]}")
            # Use the matched name for the query
            df = conn.execute(query, [matches[0]]).fetchdf()

        if len(df) == 0:
            # Still no match, show available options
            available = all_circs.head(10)
            print(f"Available circonscriptions (sample): {available['nomCirconscription'].tolist()}")
            raise HTTPException(status_code=404, detail=f"Circonscription not found: '{name}'")

    geojson_str = df_to_geojson(df)

    return Response(
        content=geojson_str,
        media_type="application/geo+json",
        headers={"Content-Disposition": f"attachment; filename=circonscription_{name}.geojson"}
    )


@app.get("/download/commune/{code}")
def download_commune(code: str):
    """Download GeoJSON for a specific commune"""

    print(f"Received commune download request for: '{code}'")

    query = """
        SELECT * FROM contours
        WHERE codeCommune = ?
    """

    df = conn.execute(query, [code]).fetchdf()

    if len(df) == 0:
        raise HTTPException(status_code=404, detail=f"Commune not found: '{code}'")

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
