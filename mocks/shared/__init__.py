"""
Shared utilities for Mock APIs

Provides common functionality across all mock API services:
- JSON fixture loading
- Health check endpoint
- Common FastAPI setup patterns
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional

from fastapi import FastAPI


def create_mock_app(
    title: str,
    description: str,
    version: str = "1.0.0",
    service_name: str = "mock-api"
) -> FastAPI:
    """
    Create a FastAPI app with standard mock API configuration.

    Args:
        title: API title for docs
        description: API description for docs
        version: API version
        service_name: Service name for health checks

    Returns:
        Configured FastAPI app with health endpoint
    """
    app = FastAPI(
        title=title,
        description=description,
        version=version
    )

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "service": service_name}

    return app


def get_data_dir() -> Path:
    """
    Get the data directory path.

    Checks for /app/data (Docker) or ./data (local development).

    Returns:
        Path to data directory
    """
    if os.path.exists("/app/data"):
        return Path("/app/data")
    return Path("./data")


def load_fixture(data_dir: Path, filename: str) -> Dict[str, Any]:
    """
    Load JSON fixture from data directory.

    Args:
        data_dir: Path to data directory
        filename: Name of JSON file to load

    Returns:
        Parsed JSON data or error dict if file not found
    """
    filepath = data_dir / filename
    if not filepath.exists():
        return {"error": f"Fixture {filename} not found"}

    with open(filepath, "r") as f:
        return json.load(f)


class MockAPIBase:
    """
    Base class for mock API services.

    Provides common fixture loading and data directory handling.

    Usage:
        class ShopifyMock(MockAPIBase):
            service_name = "mock-shopify"

            def get_products(self):
                return self.load_fixture("products.json")
    """

    service_name: str = "mock-api"

    def __init__(self, data_dir: Optional[Path] = None):
        """
        Initialize mock API base.

        Args:
            data_dir: Optional override for data directory
        """
        self.data_dir = data_dir or get_data_dir()

    def load_fixture(self, filename: str) -> Dict[str, Any]:
        """
        Load JSON fixture from data directory.

        Args:
            filename: Name of JSON file to load

        Returns:
            Parsed JSON data
        """
        return load_fixture(self.data_dir, filename)

    def fixture_exists(self, filename: str) -> bool:
        """Check if a fixture file exists."""
        return (self.data_dir / filename).exists()
