"""
Rijksmuseum Crawler

API Documentation: https://data.rijksmuseum.nl/object-metadata/api/
Requires free API key from https://data.rijksmuseum.nl/
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

SOURCE = SOURCES["rijks"]
BASE_URL = SOURCE["base_url"]

# Get API key from environment variable
API_KEY = os.environ.get("RIJKS_API_KEY", "")


def search_paintings(page: int = 1, page_size: int = 100) -> Dict:
    """
    Search for paintings in the Rijksmuseum collection.
    """
    if not API_KEY:
        print("Warning: RIJKS_API_KEY not set. Get one from https://data.rijksmuseum.nl/")
        return {"artObjects": [], "count": 0}

    url = BASE_URL

    params = {
        "key": API_KEY,
        "format": "json",
        "type": "painting",  # Only paintings
        "imgonly": True,     # Only with images
        "ps": page_size,     # Page size
        "p": page,           # Page number
        "s": "relevance",    # Sort by relevance
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error searching Rijksmuseum: {e}")
        return {"artObjects": [], "count": 0}


def get_artwork_details(object_number: str) -> Optional[Dict]:
    """
    Get detailed information about a specific artwork.
    """
    if not API_KEY:
        return None

    url = f"{BASE_URL}/{object_number}"
    params = {
        "key": API_KEY,
        "format": "json",
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json().get("artObject")
    except Exception as e:
        print(f"Error fetching artwork {object_number}: {e}")
        return None


def get_image_dimensions(image_url: str) -> Optional[tuple]:
    """
    Get image dimensions by downloading header.
    """
    try:
        from PIL import Image
        from io import BytesIO

        response = requests.get(image_url, stream=True, timeout=10)
        response.raise_for_status()

        # Download first 100KB
        chunk_size = 100 * 1024
        data = b""
        for chunk in response.iter_content(chunk_size=chunk_size):
            data += chunk
            if len(data) >= chunk_size:
                break

        img = Image.open(BytesIO(data))
        return img.size
    except:
        return None


def download_image(image_url: str, save_path: str) -> bool:
    """
    Download an image to the specified path.
    """
    try:
        response = requests.get(image_url, stream=True, timeout=120)
        response.raise_for_status()

        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        return True
    except Exception as e:
        print(f"Error downloading image: {e}")
        return False


def load_existing_metadata() -> Dict:
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"paintings": [], "sources": {}}


def save_metadata(metadata: Dict):
    os.makedirs(os.path.dirname(METADATA_FILE), exist_ok=True)
    with open(METADATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)


def crawl_rijks(limit: Optional[int] = None, skip_existing: bool = True):
    """
    Main function to crawl Rijksmuseum paintings.
    """
    if not API_KEY:
        print("Error: RIJKS_API_KEY environment variable not set")
        print("Get a free API key from: https://data.rijksmuseum.nl/")
        print("Then run: export RIJKS_API_KEY=your_key_here")
        return

    os.makedirs(PAINTINGS_DIR, exist_ok=True)

    metadata = load_existing_metadata()
    existing_ids = {p["source_id"] for p in metadata["paintings"] if p["source"] == "rijks"}

    downloaded = 0
    page = 1
    page_size = 100

    while True:
        if limit and downloaded >= limit:
            print(f"Reached limit of {limit} paintings")
            break

        print(f"\nFetching page {page}...")
        time.sleep(REQUEST_DELAY)

        result = search_paintings(page=page, page_size=page_size)
        artworks = result.get("artObjects", [])
        total_count = result.get("count", 0)

        if not artworks:
            print("No more artworks found")
            break

        for artwork in artworks:
            if limit and downloaded >= limit:
                break

            object_number = artwork.get("objectNumber")
            source_id = f"rijks_{object_number}"

            if skip_existing and source_id in existing_ids:
                continue

            # Check if has web image
            web_image = artwork.get("webImage")
            if not web_image or not web_image.get("url"):
                continue

            image_url = web_image.get("url")
            width = web_image.get("width", 0)
            height = web_image.get("height", 0)

            # Rijksmuseum provides dimensions in the API response
            if width and height:
                short_side = min(width, height)
                if short_side < MIN_SHORT_SIDE:
                    continue
            else:
                # If no dimensions, check manually
                print(f"Checking: {artwork.get('title', 'Unknown')[:50]}...")
                dims = get_image_dimensions(image_url)
                if not dims:
                    continue
                width, height = dims
                short_side = min(width, height)
                if short_side < MIN_SHORT_SIDE:
                    print(f"  Too small: {width}x{height}")
                    continue

            print(f"Processing: {artwork.get('title', 'Unknown')[:50]} ({width}x{height})")

            # Get full details
            time.sleep(REQUEST_DELAY)
            full_artwork = get_artwork_details(object_number) or {}

            # Download image
            filename = f"rijks_{object_number}.jpg"
            save_path = os.path.join(PAINTINGS_DIR, filename)

            print(f"  Downloading...")

            if download_image(image_url, save_path):
                painting_data = {
                    "id": source_id,
                    "source": "rijks",
                    "source_id": source_id,
                    "source_url": artwork.get("links", {}).get("web", f"https://www.rijksmuseum.nl/en/collection/{object_number}"),
                    "title": artwork.get("title") or full_artwork.get("title", "Untitled"),
                    "title_en": artwork.get("longTitle", ""),
                    "artist": artwork.get("principalOrFirstMaker", "Unknown"),
                    "year": full_artwork.get("dating", {}).get("presentingDate", ""),
                    "year_begin": full_artwork.get("dating", {}).get("yearEarly"),
                    "year_end": full_artwork.get("dating", {}).get("yearLate"),
                    "medium": full_artwork.get("physicalMedium", ""),
                    "dimensions_text": " x ".join(full_artwork.get("subTitle", "").split(" x ")[:2]) if full_artwork.get("subTitle") else "",
                    "description": full_artwork.get("plaqueDescriptionEnglish", ""),
                    "image_url": image_url,
                    "image_file": filename,
                    "image_width": width,
                    "image_height": height,
                    "license": SOURCE["license"],
                }

                metadata["paintings"].append(painting_data)
                metadata["sources"]["rijks"] = {
                    "name": SOURCE["name"],
                    "count": len([p for p in metadata["paintings"] if p["source"] == "rijks"]),
                    "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
                }

                save_metadata(metadata)
                downloaded += 1
                print(f"  Downloaded! Total: {downloaded}")
            else:
                print("  Failed to download")

        # Check pagination
        if page * page_size >= total_count:
            print("Reached last page")
            break

        page += 1

    print(f"\n=== Rijksmuseum Crawl Complete ===")
    print(f"Downloaded: {downloaded}")
    print(f"Total in metadata: {len(metadata['paintings'])}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Crawl Rijksmuseum for high-res paintings")
    parser.add_argument("--limit", type=int, default=None, help="Max paintings to download")
    parser.add_argument("--no-skip", action="store_true", help="Don't skip existing paintings")
    args = parser.parse_args()

    crawl_rijks(limit=args.limit, skip_existing=not args.no_skip)
