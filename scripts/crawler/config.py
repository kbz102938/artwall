"""
Crawler Configuration
"""

import os

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data")
PAINTINGS_DIR = os.path.join(DATA_DIR, "paintings")
METADATA_FILE = os.path.join(DATA_DIR, "paintings_metadata.json")

# Image requirements
MIN_WIDTH = 3200   # Minimum width in pixels
MIN_HEIGHT = 4000  # Minimum height in pixels
MIN_SHORT_SIDE = 3000  # Minimum on the shorter side

# Supported formats
SUPPORTED_FORMATS = [".jpg", ".jpeg", ".png", ".tif", ".tiff"]

# Rate limiting (seconds between requests)
REQUEST_DELAY = 0.5

# Sources
SOURCES = {
    "met": {
        "name": "Metropolitan Museum of Art",
        "base_url": "https://collectionapi.metmuseum.org/public/collection/v1",
        "license": "CC0 1.0",
    },
    "aic": {
        "name": "Art Institute of Chicago",
        "base_url": "https://api.artic.edu/api/v1",
        "iiif_url": "https://www.artic.edu/iiif/2",
        "license": "CC0 1.0",
    },
    "rijks": {
        "name": "Rijksmuseum",
        "base_url": "https://www.rijksmuseum.nl/api/en/collection",
        "license": "CC0 1.0",
        # Note: Requires API key from https://data.rijksmuseum.nl/
    },
    "nga": {
        "name": "National Gallery of Art",
        "base_url": "https://api.nga.gov",
        "license": "Public Domain",
    },
}

# Art categories to include (paintings only)
PAINTING_CLASSIFICATIONS = [
    "paintings",
    "painting",
    "oil on canvas",
    "oil painting",
    "tempera",
    "watercolor",
    "acrylic",
    "fresco",
]
