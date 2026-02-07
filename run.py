"""
Backend API Server Entry Point

Run this file to start the FastAPI server using Uvicorn.
This is the main entry point for the backend application.

Usage:
    python run.py
    
Or use uvicorn directly:
    uvicorn app.web:app --reload --host 0.0.0.0 --port 8000

Configuration:
    - Host and port are loaded from app.config (default: 0.0.0.0:8000)
    - Debug mode enables auto-reload and detailed logging
    - Set DEBUG=true in environment to enable debug mode
"""
import sys
import os

# Add backend root to Python path to enable imports
backend_root = os.path.abspath(os.path.dirname(__file__))
if backend_root not in sys.path:
    sys.path.insert(0, backend_root)

import uvicorn
from app.config import API_HOST, API_PORT, DEBUG

if __name__ == "__main__":
    # Start the FastAPI application using Uvicorn ASGI server
    # reload=True enables auto-reload on code changes (useful for development)
    # log_level controls verbosity of logging
    uvicorn.run(
        "app.web:app",           # Application module path
        host=API_HOST,            # Host address (0.0.0.0 allows external connections)
        port=API_PORT,            # Port number (default: 8000)
        reload=DEBUG,             # Auto-reload on code changes (enabled in debug mode)
        log_level="info" if not DEBUG else "debug"  # Logging verbosity
    )




