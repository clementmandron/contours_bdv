#!/bin/bash
# Quick start script for local development

echo "Starting Contours Bureaux de Vote API..."

# Activate virtual environment
source venv/bin/activate

# Start the API
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
