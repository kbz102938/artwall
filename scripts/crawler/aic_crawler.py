"""
Art Institute of Chicago Crawler

API Documentation: https://api.artic.edu/docs/
Uses IIIF for high-resolution images
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

SOURCE = SOURCES["aic"]
BASE_URL = SOURCE["base_url"]
IIIF_URL = SOURCE["iiif_url"]


def search_paintings(page: int = 1, limit: int = 100) -> Dict:
    """
    Search for paintings in the AIC collection.
    """
    url = f"{BASE_URL}/artworks/search"

    # Search for paintings that are public domain
    params = {
        "q": "painting",
        "query": {
            "bool": {
                "must": [
                    {"term": {"is_public_domain": True}},
                    {"exists": {"field": "image_id"}},
                ],
                "should": [
                    {"match": {"artwork_type_title": "Painting"}},
                    {"match": {"classification_title": "painting"}},
                    {"match": {"medium_display": "oil on canvas"}},
                ]
            }
        },
        "fields": [
            "id",
            "title",
            "artist_display",
            "date_display",
            "date_start",
            "date_end",
            "medium_display",
            "dimensions",
            "artwork_type_title",
            "classification_title",
            "image_id",
            "thumbnail",
            "is_public_domain",
        ],
        "limit": limit,
        "page": page,
    }

    headers = {"Content-Type": "application/json"}

    try:
        response = requests.post(url, json=params, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error searching AIC: {e}")
        return {"data": [], "pagination": {}}


def get_artwork_details(artwork_id: int) -> Optional[Dict]:
    """
    Get detailed information about a specific artwork.
    """
    url = f"{BASE_URL}/artworks/{artwork_id}"
    params = {
        "fields": "id,title,artist_display,artist_title,date_display,date_start,date_end,"
                  "medium_display,dimensions,artwork_type_title,classification_title,"
                  "image_id,is_public_domain,credit_line,place_of_origin,style_title,"
                  "thumbnail"
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json().get("data")
    except Exception as e:
        print(f"Error fetching artwork {artwork_id}: {e}")
        return None


def get_iiif_image_info(image_id: str) -> Optional[Dict]:
    """
    Get IIIF image info to check dimensions.
    """
    info_url = f"{IIIF_URL}/{image_id}/info.json"

    try:
        response = requests.get(info_url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error getting IIIF info: {e}")
        return None


def get_iiif_image_url(image_id: str, max_size: int = 3000) -> str:
    """
    Construct IIIF URL for downloading image.
    Using 'full' region and specific max size.
    """
    # IIIF format: {scheme}://{server}/{prefix}/{identifier}/{region}/{size}/{rotation}/{quality}.{format}
    # For max resolution: full/full/0/default.jpg
    # For specific max size: full/!3000,3000/0/default.jpg
    return f"{IIIF_URL}/{image_id}/full/full/0/default.jpg"


def is_valid_painting(artwork: Dict) -> bool:
    """
    Check if the artwork is a valid painting.
    """
    if not artwork.get("is_public_domain"):
        return False

    if not artwork.get("image_id"):
        return False

    artwork_type = (artwork.get("artwork_type_title") or "").lower()
    classification = (artwork.get("classification_title") or "").lower()
    medium = (artwork.get("medium_display") or "").lower()

    painting_keywords = ["painting", "oil", "canvas", "tempera", "watercolor", "acrylic", "fresco", "panel"]

    return any(kw in artwork_type for kw in painting_keywords) or \
           any(kw in classification for kw in painting_keywords) or \
           any(kw in medium for kw in painting_keywords)


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


def crawl_aic(limit: Optional[int] = None, skip_existing: bool = True):
    """
    Main function to crawl Art Institute of Chicago paintings.

    Args:
        limit: Maximum number of paintings to download (None for all)
        skip_existing: Skip paintings already in metadata
    """
    os.makedirs(PAINTINGS_DIR, exist_ok=True)

    # Load existing metadata
    metadata = load_existing_metadata()
    existing_ids = {p["source_id"] for p in metadata["paintings"] if p["source"] == "aic"}

    downloaded = 0
    page = 1
    per_page = 100

    while True:
        if limit and downloaded >= limit:
            print(f"Reached limit of {limit} paintings")
            break

        print(f"\nFetching page {page}...")
        time.sleep(REQUEST_DELAY)

        # Search for artworks
        result = search_paintings(page=page, limit=per_page)
        artworks = result.get("data", [])
        pagination = result.get("pagination", {})

        if not artworks:
            print("No more artworks found")
            break

        for artwork in artworks:
            if limit and downloaded >= limit:
                break

            artwork_id = artwork.get("id")
            source_id = f"aic_{artwork_id}"

            # Skip if already downloaded
            if skip_existing and source_id in existing_ids:
                continue

            # Check if valid painting
            if not is_valid_painting(artwork):
                continue

            image_id = artwork.get("image_id")
            if not image_id:
                continue

            # Get image info for dimensions
            print(f"Checking: {artwork.get('title', 'Unknown')[:50]}...")
            time.sleep(REQUEST_DELAY)

            image_info = get_iiif_image_info(image_id)
            if not image_info:
                print("  Could not get image info, skipping")
                continue

            width = image_info.get("width", 0)
            height = image_info.get("height", 0)
            short_side = min(width, height)

            if short_side < MIN_SHORT_SIDE:
                print(f"  Too small: {width}x{height} (need {MIN_SHORT_SIDE}px min)")
                continue

            print(f"  Good size: {width}x{height}")

            # Get full artwork details
            full_artwork = get_artwork_details(artwork_id) or artwork

            # Download the image
            filename = f"aic_{artwork_id}.jpg"
            save_path = os.path.join(PAINTINGS_DIR, filename)
            image_url = get_iiif_image_url(image_id)

            print(f"  Downloading...")

            if download_image(image_url, save_path):
                # Add to metadata
                painting_data = {
                    "id": source_id,
                    "source": "aic",
                    "source_id": source_id,
                    "source_url": f"https://www.artic.edu/artworks/{artwork_id}",
                    "title": full_artwork.get("title", "Untitled"),
                    "artist": full_artwork.get("artist_display", "Unknown"),
                    "artist_name": full_artwork.get("artist_title", ""),
                    "year": full_artwork.get("date_display", ""),
                    "year_begin": full_artwork.get("date_start"),
                    "year_end": full_artwork.get("date_end"),
                    "medium": full_artwork.get("medium_display", ""),
                    "dimensions_text": full_artwork.get("dimensions", ""),
                    "classification": full_artwork.get("classification_title", ""),
                    "artwork_type": full_artwork.get("artwork_type_title", ""),
                    "style": full_artwork.get("style_title", ""),
                    "origin": full_artwork.get("place_of_origin", ""),
                    "credit": full_artwork.get("credit_line", ""),
                    "image_id": image_id,
                    "image_url": image_url,
                    "image_file": filename,
                    "image_width": width,
                    "image_height": height,
                    "license": SOURCE["license"],
                }

                metadata["paintings"].append(painting_data)
                metadata["sources"]["aic"] = {
                    "name": SOURCE["name"],
                    "count": len([p for p in metadata["paintings"] if p["source"] == "aic"]),
                    "last_updated": time.strftime("%Y-%m-%d %H:%M:%S"),
                }

                # Save metadata after each download
                save_metadata(metadata)

                downloaded += 1
                print(f"  Downloaded! Total: {downloaded}")
            else:
                print("  Failed to download")

        # Check if there are more pages
        total_pages = pagination.get("total_pages", 1)
        if page >= total_pages:
            print("Reached last page")
            break

        page += 1

    print(f"\n=== Art Institute of Chicago Crawl Complete ===")
    print(f"Downloaded: {downloaded}")
    print(f"Total in metadata: {len(metadata['paintings'])}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Crawl Art Institute of Chicago for high-res paintings")
    parser.add_argument("--limit", type=int, default=None, help="Max paintings to download")
    parser.add_argument("--no-skip", action="store_true", help="Don't skip existing paintings")
    args = parser.parse_args()

    crawl_aic(limit=args.limit, skip_existing=not args.no_skip)
