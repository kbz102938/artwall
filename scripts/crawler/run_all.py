#!/usr/bin/env python3
"""
Run all painting crawlers

Usage:
    python run_all.py --limit 100       # Download 100 from each source
    python run_all.py --source met      # Only Met Museum
    python run_all.py                   # Download all available
"""

import argparse
import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    parser = argparse.ArgumentParser(description="Crawl museums for high-res paintings")
    parser.add_argument("--limit", type=int, default=None,
                        help="Max paintings per source (default: no limit)")
    parser.add_argument("--source", type=str, choices=["met", "aic", "rijks", "all"],
                        default="all", help="Which source to crawl")
    parser.add_argument("--no-skip", action="store_true",
                        help="Don't skip existing paintings")
    args = parser.parse_args()

    skip_existing = not args.no_skip

    print("=" * 60)
    print("ArtWall Painting Crawler")
    print("=" * 60)
    print(f"Limit per source: {args.limit or 'No limit'}")
    print(f"Skip existing: {skip_existing}")
    print(f"Sources: {args.source}")
    print("=" * 60)

    if args.source in ["met", "all"]:
        print("\n>>> Starting Metropolitan Museum of Art crawler...")
        try:
            from met_crawler import crawl_met
            crawl_met(limit=args.limit, skip_existing=skip_existing)
        except Exception as e:
            print(f"Met crawler error: {e}")

    if args.source in ["aic", "all"]:
        print("\n>>> Starting Art Institute of Chicago crawler...")
        try:
            from aic_crawler import crawl_aic
            crawl_aic(limit=args.limit, skip_existing=skip_existing)
        except Exception as e:
            print(f"AIC crawler error: {e}")

    if args.source in ["rijks", "all"]:
        print("\n>>> Starting Rijksmuseum crawler...")
        if not os.environ.get("RIJKS_API_KEY"):
            print("Skipping Rijksmuseum - RIJKS_API_KEY not set")
            print("Get a free key from: https://data.rijksmuseum.nl/")
        else:
            try:
                from rijks_crawler import crawl_rijks
                crawl_rijks(limit=args.limit, skip_existing=skip_existing)
            except Exception as e:
                print(f"Rijks crawler error: {e}")

    # Print summary
    print("\n" + "=" * 60)
    print("CRAWL COMPLETE")
    print("=" * 60)

    from config import METADATA_FILE, PAINTINGS_DIR
    import json

    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, 'r') as f:
            metadata = json.load(f)

        print(f"\nTotal paintings downloaded: {len(metadata.get('paintings', []))}")
        print("\nBy source:")
        for source, info in metadata.get("sources", {}).items():
            print(f"  - {info.get('name', source)}: {info.get('count', 0)}")

        # Calculate total size
        total_size = 0
        for f in os.listdir(PAINTINGS_DIR):
            fp = os.path.join(PAINTINGS_DIR, f)
            if os.path.isfile(fp):
                total_size += os.path.getsize(fp)

        print(f"\nTotal disk usage: {total_size / (1024*1024*1024):.2f} GB")
        print(f"Paintings folder: {PAINTINGS_DIR}")
        print(f"Metadata file: {METADATA_FILE}")


if __name__ == "__main__":
    main()
