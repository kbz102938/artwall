#!/usr/bin/env python3
"""
Direct ingest: Load CLIP model locally and insert paintings into database.
No HTTP service needed.
"""

import json
import sys
import psycopg2
from pathlib import Path

# Add clip-service to path
sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "clip-service"))

from app.services.embedding import EmbeddingService

# Configuration
DATA_DIR = Path(__file__).parent.parent / "data" / "paintings"
METADATA_FILE = Path(__file__).parent.parent / "data" / "paintings_metadata.json"
DATABASE_URL = "postgresql://postgres:artwall2024@136.111.179.100:5432/artwall"


def insert_painting(cursor, painting, embedding):
    """Insert painting with embedding into database."""
    painting_id = painting["id"]
    title = painting.get("title", "Untitled")
    artist = painting.get("artist_name") or painting.get("artist", "Unknown")

    year_begin = painting.get("year_begin")
    year = int(year_begin) if year_begin else None

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
    print("=" * 50)
    print("ArtWall Direct Ingest Script")
    print("=" * 50)

    # Load metadata
    print(f"\n1. Loading metadata from {METADATA_FILE}...")
    with open(METADATA_FILE, "r") as f:
        data = json.load(f)

    paintings = data.get("paintings", [])
    print(f"   Found {len(paintings)} paintings")

    # Initialize embedding service (this loads the CLIP model)
    print("\n2. Loading CLIP model (this may take a minute)...")
    embedding_service = EmbeddingService()
    print("   CLIP model loaded!")

    # Connect to database
    print("\n3. Connecting to database...")
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    print("   Connected!")

    # Process paintings
    print("\n4. Processing paintings...")
    success_count = 0
    error_count = 0

    for i, painting in enumerate(paintings):
        painting_id = painting["id"]
        image_file = painting.get("image_file")

        if not image_file:
            print(f"   [{i+1}/{len(paintings)}] {painting_id}: No image file, skipping")
            continue

        image_path = DATA_DIR / image_file
        if not image_path.exists():
            print(f"   [{i+1}/{len(paintings)}] {painting_id}: Image not found, skipping")
            continue

        try:
            # Get embedding
            embedding = embedding_service.get_embedding_from_file(str(image_path))

            # Insert into database
            insert_painting(cursor, painting, embedding)
            conn.commit()

            print(f"   [{i+1}/{len(paintings)}] {painting_id}: OK (dim={len(embedding)})")
            success_count += 1

        except Exception as e:
            print(f"   [{i+1}/{len(paintings)}] {painting_id}: ERROR - {e}")
            error_count += 1
            conn.rollback()

    cursor.close()
    conn.close()

    print("\n" + "=" * 50)
    print(f"Done! Success: {success_count}, Errors: {error_count}")
    print("=" * 50)


if __name__ == "__main__":
    main()
