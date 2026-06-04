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

# Master switch for all database-backed features (weather cache, recommendation
# history, user/settings/auth endpoints). Temporarily disabled while there is no
# real Postgres provisioned — the app still serves weather + scoring without it.
# To re-enable: set DB_ENABLED=true AND point DATABASE_URL at a real database.
DB_ENABLED = os.getenv("DB_ENABLED", "false").lower() == "true"

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

# JWT Configuration
# Set JWT_SECRET to a long random string in production — never use the default
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))  # 24 hours

