"""
Configuration settings for the application.

This module loads configuration from environment variables with sensible defaults.
All configuration values can be overridden via environment variables or a .env file.

Configuration includes:
- Database connection settings
- API server host and port
- Debug mode
- Application metadata
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

# Database Configuration
# PostgreSQL connection string in format: postgresql://user:password@host:port/database
# Can be overridden via DATABASE_URL environment variable
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:pukan2001@localhost:1234/weather_cloth_rec"
)

# API Configuration
# Host address to bind the server (0.0.0.0 allows external connections)
API_HOST = os.getenv("API_HOST", "0.0.0.0")

# Port number for the API server
API_PORT = int(os.getenv("API_PORT", 8000))

# Debug mode enables detailed error messages and auto-reload
# Set DEBUG=true in environment to enable
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# Application Metadata
# Used in API documentation and health check responses
APP_NAME = "Weather Clothing Recommendation API"
APP_VERSION = "1.0.0"

