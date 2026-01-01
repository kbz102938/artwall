"""
Metropolitan Museum of Art Crawler

API Documentation: https://metmuseum.github.io/
All images are CC0 (public domain)
"""

import os
import json
import time
import requests
from typing import Optional, Dict, List
from config import (
    PAINTINGS_DIR, METADATA_FILE, MIN_SHORT_SIDE,
    REQUEST_DELAY, SOURCES
)

SOURCE = SOURCES["met"]
BASE_URL = SOURCE["base_url"]


def get_painting_ids() -> List[int]:
    """
    Get all object IDs for paintings in the Met's collection.
    """
    print("Fetching painting IDs from Met Museum...")

    # Search for paintings that are public domain and have images
    url = f"{BASE_URL}/search"
    params = {
        "hasImages": True,
        "isPublicDomain": True,
        "q": "painting",  # Search term
    }

    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()

    object_ids = data.get("objectIDs", [])
    print(f"Found {len(object_ids)} potential paintings")

    return object_ids


def get_object_details(object_id: int) -> Optional[Dict]:
    """
    Get detailed information about a specific object.
    """
    url = f"{BASE_URL}/objects/{object_id}"

    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching object {object_id}: {e}")
        return None


def is_valid_painting(obj: Dict) -> bool:
    """
    Check if the object is a valid painting for our use.
    """
    # Must be public domain
    if not obj.get("isPublicDomain"):
        return False

    # Must have a primary image
    if not obj.get("primaryImage"):
        return False

    # Should be a painting (check classification and medium)
    classification = (obj.get("classification") or "").lower()
    medium = (obj.get("medium") or "").lower()
    object_name = (obj.get("objectName") or "").lower()

    painting_keywords = ["painting", "oil", "canvas", "tempera", "watercolor", "acrylic", "fresco"]

    is_painting = any(kw in classification for kw in painting_keywords) or \
                  any(kw in medium for kw in painting_keywords) or \
                  any(kw in object_name for kw in painting_keywords)

    return is_painting


def get_image_dimensions(image_url: str) -> Optional[tuple]:
    """
    Get image dimensions by fetching headers (if available) or downloading partially.
    For Met images, we'll need to download and check.
    """
    try:
        # Try to get dimensions from a small download
        response = requests.get(image_url, stream=True, timeout=10)
        response.raise_for_status()

        # Download just enough to read image header
        from PIL import Image
        from io import BytesIO

        # Download first 100KB to get dimensions
        chunk_size = 100 * 1024
        data = b""
        for chunk in response.iter_content(chunk_size=chunk_size):
            data += chunk
            if len(data) >= chunk_size:
                break

        try:
            img = Image.open(BytesIO(data))
            return img.size  # (width, height)
        except:
            return None

    except Exception as e:
        print(f"Error checking image dimensions: {e}")
        return None


def download_image(image_url: str, save_path: str) -> bool:
    """
    Download an image to the specified path.
    """
    try:
        response = requests.get(image_url, stream=True, timeout=60)
        response.raise_for_status()

        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        return True
    except Exception as e:
        print(f"Error downloading image: {e}")
        return False


def load_existing_metadata() -> Dict:
    """
    Load existing metadata file if it exists.
    """
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"paintings": [], "sources": {}}


def save_metadata(metadata: Dict):
    """
    Save metadata to file.
    """
    os.makedirs(os.path.dirname(METADATA_FILE), exist_ok=True)
    with open(METADATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)


def crawl_met(limit: Optional[int] = None, skip_existing: bool = True):
    """
    Main function to crawl Met Museum paintings.

    Args:
        limit: Maximum number of paintings to download (None for all)
        skip_existing: Skip paintings already in metadata
    """
    os.makedirs(PAINTINGS_DIR, exist_ok=True)

    # Load existing metadata
    metadata = load_existing_metadata()
    existing_ids = {p["source_id"] for p in metadata["paintings"] if p["source"] == "met"}

    # Get all painting IDs
    object_ids = get_painting_ids()

    downloaded = 0
    checked = 0

    for obj_id in object_ids:
        if limit and downloaded >= limit:
            print(f"Reached limit of {limit} paintings")
            break

        # Skip if already downloaded
        if skip_existing and f"met_{obj_id}" in existing_ids:
            continue

        checked += 1
        if checked % 100 == 0:
            print(f"Checked {checked} objects, downloaded {downloaded} paintings...")

        # Rate limiting
        time.sleep(REQUEST_DELAY)

        # Get object details
        obj = get_object_details(obj_id)
        if not obj:
            continue

        # Check if valid painting
        if not is_valid_painting(obj):
            continue

        image_url = obj.get("primaryImage")
        if not image_url:
            continue

        # Check image dimensions
        print(f"Checking dimensions for: {obj.get('title', 'Unknown')[:50]}...")
        dimensions = get_image_dimensions(image_url)

        if not dimensions:
            print("  Could not get dimensions, skipping")
            continue

        width, height = dimensions
        short_side = min(width, height)

        if short_side < MIN_SHORT_SIDE:
            print(f"  Too small: {width}x{height} (need {MIN_SHORT_SIDE}px min)")
            continue

        print(f"  Good size: {width}x{height}")

        # Download the image
        filename = f"met_{obj_id}.jpg"
        save_path = os.path.join(PAINTINGS_DIR, filename)

        print(f"  Downloading: {obj.get('title', 'Unknown')[:50]}...")

        if download_image(image_url, save_path):
            # Add to metadata
            painting_data = {
                "id": f"met_{obj_id}",
                "source": "met",
                "source_id": f"met_{obj_id}",
                "source_url": obj.get("objectURL", ""),
                "title": obj.get("title", "Untitled"),
                "artist": obj.get("artistDisplayName", "Unknown"),
                "artist_bio": obj.get("artistDisplayBio", ""),
                "year": obj.get("objectDate", ""),
                "year_begin": obj.get("objectBeginDate"),
                "year_end": obj.get("objectEndDate"),
                "medium": obj.get("medium", ""),
                "dimensions_text": obj.get("dimensions", ""),
                "classification": obj.get("classification", ""),
                "department": obj.get("department", ""),
                "culture": obj.get("culture", ""),
                "period": obj.get("period", ""),
                "image_url": image_url,
                "image_file": filename,
                "image_width": width,
                "image_height": height,
                "license": SOURCE["license"],
            }

            metadata["paintings"].append(painting_data)
            metadata["sources"]["met"] = {
                "name": SOURCE["name"],
                "count": len([p for p in metadata["paintings"] if p["source"] == "met"]),
                "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
            }

            # Save metadata after each download
            save_metadata(metadata)

            downloaded += 1
            print(f"  Downloaded! Total: {downloaded}")
        else:
            print("  Failed to download")

    print(f"\n=== Met Museum Crawl Complete ===")
    print(f"Checked: {checked}")
    print(f"Downloaded: {downloaded}")
    print(f"Total in metadata: {len(metadata['paintings'])}")


if __name__ == "__main__":
    # Install required packages first:
    # pip install requests pillow

    import argparse
    parser = argparse.ArgumentParser(description="Crawl Met Museum for high-res paintings")
    parser.add_argument("--limit", type=int, default=None, help="Max paintings to download")
    parser.add_argument("--no-skip", action="store_true", help="Don't skip existing paintings")
    args = parser.parse_args()

    crawl_met(limit=args.limit, skip_existing=not args.no_skip)
