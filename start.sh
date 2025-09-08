#!/bin/bash

# Print environment info for debugging
echo "Starting PDF Compressor..."
echo "Port: ${PORT:-8080}"
echo "Checking for Ghostscript..."
which gs || which ghostscript || echo "Ghostscript not found in PATH"

# Start the application
exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080}