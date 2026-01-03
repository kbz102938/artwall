#!/usr/bin/env python3
"""
Crawl paintings from Met Museum, upload to GCS, and save to database.

Usage:
    1. Make sure Cloud SQL proxy is running: cloud-sql-proxy artwall-483011:us-central1:artwall-db --port 5432
    2. Run: python scripts/crawl_and_upload.py --limit 100
"""

import os
import sys
import time
import json
import requests
import psycopg2
from io import BytesIO
from PIL import Image
from datetime import datetime

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configuration
GCS_BUCKET = "artwall-user-content"
GCS_PAINTINGS_PREFIX = "paintings"
DATABASE_URL = "postgresql://postgres:artwall2024@127.0.0.1:5432/artwall"
MET_API_BASE = "https://collectionapi.metmuseum.org/public/collection/v1"
REQUEST_DELAY = 0.3
MIN_SHORT_SIDE = 800  # Lowered for more results

# Try to import google cloud storage
try:
    from google.cloud import storage
    HAS_GCS = True
except ImportError:
    HAS_GCS = False
    print("Warning: google-cloud-storage not installed, will use gsutil instead")


def get_painting_ids():
    """Get all painting IDs from Met Museum API."""
    print("Fetching painting IDs from Met Museum...")
    url = f"{MET_API_BASE}/search"
    params = {
        "hasImages": True,
        "isPublicDomain": True,
        "q": "painting",
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()
    object_ids = data.get("objectIDs", [])
    print(f"Found {len(object_ids)} potential paintings")
    return object_ids


def get_object_details(object_id):
    """Get detailed information about a specific object."""
    url = f"{MET_API_BASE}/objects/{object_id}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching object {object_id}: {e}")
        return None


def is_valid_painting(obj):
    """Check if the object is a valid painting."""
    if not obj.get("isPublicDomain"):
        return False
    if not obj.get("primaryImage"):
        return False

    classification = (obj.get("classification") or "").lower()
    medium = (obj.get("medium") or "").lower()
    object_name = (obj.get("objectName") or "").lower()

    painting_keywords = ["painting", "oil", "canvas", "tempera", "watercolor", "acrylic", "fresco"]

    return any(kw in classification for kw in painting_keywords) or \
           any(kw in medium for kw in painting_keywords) or \
           any(kw in object_name for kw in painting_keywords)


def download_image(url):
    """Download image and return PIL Image and bytes."""
    try:
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        img_bytes = response.content
        img = Image.open(BytesIO(img_bytes))
        return img, img_bytes
    except Exception as e:
        print(f"Error downloading image: {e}")
        return None, None


def upload_to_gcs(img_bytes, filename):
    """Upload image bytes to GCS and return public URL."""
    blob_path = f"{GCS_PAINTINGS_PREFIX}/{filename}"

    if HAS_GCS:
        client = storage.Client(project="artwall-483011")
        bucket = client.bucket(GCS_BUCKET)
        blob = bucket.blob(blob_path)
        blob.upload_from_string(img_bytes, content_type="image/jpeg")
        return f"https://storage.googleapis.com/{GCS_BUCKET}/{blob_path}"
    else:
        # Fallback to gsutil
        import subprocess
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            f.write(img_bytes)
            temp_path = f.name

        try:
            gcs_path = f"gs://{GCS_BUCKET}/{blob_path}"
            subprocess.run(["gsutil", "cp", temp_path, gcs_path], check=True, capture_output=True)
            return f"https://storage.googleapis.com/{GCS_BUCKET}/{blob_path}"
        finally:
            os.unlink(temp_path)


def get_existing_ids(cursor):
    """Get set of existing painting IDs in database."""
    cursor.execute("SELECT id FROM paintings WHERE id LIKE 'met_%'")
    return {row[0] for row in cursor.fetchall()}


def insert_painting(cursor, painting_data):
    """Insert painting into database."""
    cursor.execute("""
        INSERT INTO paintings (
            id, title, artist, year, style,
            image_url, source, source_url, license,
            aspect_ratio,
            created_at, updated_at
        ) VALUES (
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s,
            NOW(), NOW()
        )
        ON CONFLICT (id) DO UPDATE SET
            image_url = EXCLUDED.image_url,
            updated_at = NOW()
    """, (
        painting_data["id"],
        painting_data["title"],
        painting_data["artist"],
        painting_data["year"],
        painting_data["style"],
        painting_data["image_url"],
        painting_data["source"],
        painting_data["source_url"],
        painting_data["license"],
        painting_data["aspect_ratio"],
    ))


def main(limit=100):
    print(f"Crawling {limit} paintings from Met Museum...")
    print(f"Will upload to GCS bucket: {GCS_BUCKET}")

    # Connect to database
    print("Connecting to database...")
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    # Get existing IDs
    existing_ids = get_existing_ids(cursor)
    print(f"Found {len(existing_ids)} existing Met paintings in database")

    # Get all painting IDs
    object_ids = get_painting_ids()

    downloaded = 0
    checked = 0

    for obj_id in object_ids:
        if downloaded >= limit:
            print(f"\nReached limit of {limit} paintings")
            break

        painting_id = f"met_{obj_id}"

        # Skip if already exists
        if painting_id in existing_ids:
            continue

        checked += 1
        if checked % 50 == 0:
            print(f"Checked {checked} objects, downloaded {downloaded} paintings...")

        time.sleep(REQUEST_DELAY)

        # Get object details
        obj = get_object_details(obj_id)
        if not obj:
            continue

        if not is_valid_painting(obj):
            continue

        image_url = obj.get("primaryImage")
        if not image_url:
            continue

        # Download image
        title = obj.get("title", "Untitled")[:50]
        print(f"Downloading: {title}...")

        img, img_bytes = download_image(image_url)
        if not img:
            continue

        width, height = img.size
        short_side = min(width, height)

        if short_side < MIN_SHORT_SIDE:
            print(f"  Too small: {width}x{height}")
            continue

        # Upload to GCS
        filename = f"{painting_id}.jpg"
        print(f"  Uploading to GCS...")

        try:
            gcs_url = upload_to_gcs(img_bytes, filename)
            print(f"  Uploaded: {gcs_url}")
        except Exception as e:
            print(f"  GCS upload failed: {e}")
            continue

        # Calculate aspect ratio
        if width > height:
            aspect_ratio = "landscape"
        elif height > width:
            aspect_ratio = "portrait"
        else:
            aspect_ratio = "square"

        # Get year
        year = obj.get("objectBeginDate")
        if year:
            try:
                year = int(year)
            except:
                year = None

        # Insert into database
        painting_data = {
            "id": painting_id,
            "title": obj.get("title", "Untitled"),
            "artist": obj.get("artistDisplayName", "Unknown"),
            "year": year,
            "style": obj.get("classification"),
            "image_url": gcs_url,  # Use GCS URL instead of Met URL
            "source": "met",
            "source_url": obj.get("objectURL", ""),
            "license": "CC0 1.0",
            "aspect_ratio": aspect_ratio,
        }

        try:
            insert_painting(cursor, painting_data)
            conn.commit()
            downloaded += 1
            print(f"  Saved! Total: {downloaded}/{limit}")
        except Exception as e:
            print(f"  DB insert failed: {e}")
            conn.rollback()

    cursor.close()
    conn.close()

    print(f"\n{'='*50}")
    print(f"Crawl complete!")
    print(f"Checked: {checked}")
    print(f"Downloaded: {downloaded}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Crawl Met Museum paintings to GCS")
    parser.add_argument("--limit", type=int, default=100, help="Max paintings to download")
    args = parser.parse_args()

    main(limit=args.limit)
