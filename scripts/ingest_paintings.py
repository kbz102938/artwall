#!/usr/bin/env python3
"""
Ingest paintings: call CLIP service for embeddings and insert into database.

Usage:
    1. Start the CLIP service: cd apps/clip-service && python -m uvicorn app.main:app --port 8080
    2. Run this script: python scripts/ingest_paintings.py
"""

import json
import requests
import psycopg2
from pathlib import Path

# Configuration
DATA_DIR = Path(__file__).parent.parent / "data" / "paintings"
METADATA_FILE = Path(__file__).parent.parent / "data" / "paintings_metadata.json"
DATABASE_URL = "postgresql://postgres:artwall2024@136.111.179.100:5432/artwall"
CLIP_SERVICE_URL = "http://localhost:8080"

BATCH_SIZE = 5  # Process 5 at a time


def get_embeddings_batch(files):
    """Call CLIP service batch endpoint."""
    response = requests.post(
        f"{CLIP_SERVICE_URL}/api/embedding/file/batch",
        json={"files": files},
        timeout=120
    )
    response.raise_for_status()
    return response.json()["results"]


def parse_year(painting):
    """Extract year from painting metadata."""
    year_begin = painting.get("year_begin")
    if year_begin:
        return int(year_begin)
    return None


def insert_painting(cursor, painting, embedding):
    """Insert painting with embedding into database."""
    painting_id = painting["id"]
    title = painting.get("title", "Untitled")
    artist = painting.get("artist_name") or painting.get("artist", "Unknown")
    year = parse_year(painting)
    style = painting.get("style")
    image_url = painting.get("image_url", "")
    source = painting.get("source", "")
    source_url = painting.get("source_url", "")
    license_info = painting.get("license", "")

    # Calculate aspect ratio
    width = painting.get("image_width", 1)
    height = painting.get("image_height", 1)
    if width > height:
        aspect_ratio = "landscape"
    elif height > width:
        aspect_ratio = "portrait"
    else:
        aspect_ratio = "square"

    # Format embedding for pgvector
    embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"

    cursor.execute("""
        INSERT INTO paintings (
            id, title, artist, year, style,
            image_url, source, source_url, license,
            aspect_ratio, embedding,
            created_at, updated_at
        ) VALUES (
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s::vector,
            NOW(), NOW()
        )
        ON CONFLICT (id) DO UPDATE SET
            embedding = EXCLUDED.embedding,
            updated_at = NOW()
    """, (
        painting_id, title, artist, year, style,
        image_url, source, source_url, license_info,
        aspect_ratio, embedding_str
    ))


def main():
    # Load metadata
    print(f"Loading metadata from {METADATA_FILE}...")
    with open(METADATA_FILE, "r") as f:
        data = json.load(f)

    paintings = data.get("paintings", [])
    print(f"Found {len(paintings)} paintings")

    # Check CLIP service health
    try:
        health = requests.get(f"{CLIP_SERVICE_URL}/health", timeout=5)
        print(f"CLIP service: {health.json()}")
    except Exception as e:
        print(f"ERROR: Cannot reach CLIP service at {CLIP_SERVICE_URL}")
        print(f"Start it with: cd apps/clip-service && python -m uvicorn app.main:app --port 8080")
        return

    # Connect to database
    print("Connecting to database...")
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    # Build file list
    files_to_process = []
    paintings_map = {}

    for painting in paintings:
        painting_id = painting["id"]
        image_file = painting.get("image_file")

        if not image_file:
            print(f"  {painting_id}: No image file, skipping")
            continue

        image_path = DATA_DIR / image_file
        if not image_path.exists():
            print(f"  {painting_id}: Image not found, skipping")
            continue

        files_to_process.append({
            "id": painting_id,
            "filePath": str(image_path.absolute())
        })
        paintings_map[painting_id] = painting

    print(f"\nProcessing {len(files_to_process)} paintings in batches of {BATCH_SIZE}...")

    success_count = 0
    error_count = 0

    # Process in batches
    for i in range(0, len(files_to_process), BATCH_SIZE):
        batch = files_to_process[i:i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        total_batches = (len(files_to_process) + BATCH_SIZE - 1) // BATCH_SIZE

        print(f"\nBatch {batch_num}/{total_batches} ({len(batch)} paintings)...")

        try:
            results = get_embeddings_batch(batch)

            for result in results:
                painting_id = result["id"]
                painting = paintings_map[painting_id]

                if "error" in result:
                    print(f"  {painting_id}: ERROR - {result['error']}")
                    error_count += 1
                    continue

                embedding = result["embedding"]
                insert_painting(cursor, painting, embedding)
                print(f"  {painting_id}: OK (dim={len(embedding)})")
                success_count += 1

            conn.commit()

        except Exception as e:
            print(f"  Batch error: {e}")
            error_count += len(batch)
            conn.rollback()

    cursor.close()
    conn.close()

    print(f"\n{'='*40}")
    print(f"Done! Success: {success_count}, Errors: {error_count}")


if __name__ == "__main__":
    main()
