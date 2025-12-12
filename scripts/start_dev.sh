#!/bin/bash

# Start development server

echo "Starting FastAPI development server..."
echo "Server will be available at: http://localhost:8000"
echo "API Documentation: http://localhost:8000/docs"
echo ""

cd "$(dirname "$0")/.."

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run server
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
