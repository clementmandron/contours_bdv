#!/usr/bin/env python3
"""
Download GeoJSON from data.gouv.fr and convert to Parquet.
"""

import requests
import geopandas as gpd
from pathlib import Path

# Official GeoJSON URL
GEOJSON_URL = "https://www.data.gouv.fr/api/1/datasets/r/f98165a7-7c37-4705-a181-bcfc943edc73"

def main():
    # Setup paths
    data_dir = Path(__file__).parent.parent / "data"
    data_dir.mkdir(exist_ok=True)

    print("Downloading GeoJSON (~615MB)...")
    response = requests.get(GEOJSON_URL, timeout=300)
    response.raise_for_status()

    print("Converting to Parquet...")
    gdf = gpd.read_file(response.content)

    output_file = data_dir / "contours_bureaux_vote.parquet"
    gdf.to_parquet(output_file, compression='snappy')

    print(f"✓ Done! Saved to {output_file}")
    print(f"  Features: {len(gdf)}")

if __name__ == "__main__":
    main()
