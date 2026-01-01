# ArtWall Painting Crawler

Downloads high-resolution public domain paintings from museum APIs.

## Requirements

- Python 3.8+
- ~3GB+ disk space (depending on how many paintings)

## Setup

```bash
cd scripts/crawler
pip install -r requirements.txt
```

## Usage

### Download from all sources (with limit)
```bash
python run_all.py --limit 50
```

### Download from specific source
```bash
python run_all.py --source met --limit 100
python run_all.py --source aic --limit 100
python run_all.py --source rijks --limit 100
```

### Download all available paintings (no limit)
```bash
python run_all.py
```

## Sources

| Source | API Key Required | Notes |
|--------|------------------|-------|
| Metropolitan Museum of Art | No | ~400k open access works |
| Art Institute of Chicago | No | ~50k open access works, IIIF support |
| Rijksmuseum | Yes (free) | Get key from https://data.rijksmuseum.nl/ |

### Setting up Rijksmuseum API Key

1. Go to https://data.rijksmuseum.nl/
2. Create an account and request an API key
3. Set the environment variable:
   ```bash
   export RIJKS_API_KEY=your_key_here
   ```

## Output

- **Images**: `data/paintings/` - Downloaded painting images
- **Metadata**: `data/paintings_metadata.json` - Painting info (title, artist, dimensions, etc.)

## Image Requirements

Only downloads images with:
- Minimum 3000px on the short side
- Suitable for printing up to 80×100cm at 200 DPI

## Metadata Schema

```json
{
  "id": "met_12345",
  "source": "met",
  "source_url": "https://...",
  "title": "The Starry Night",
  "artist": "Vincent van Gogh",
  "year": "1889",
  "medium": "Oil on canvas",
  "image_file": "met_12345.jpg",
  "image_width": 5000,
  "image_height": 6000,
  "license": "CC0 1.0"
}
```

## Notes

- Respects rate limiting (0.5s between requests)
- Skips already downloaded paintings
- Saves metadata after each download (resume-safe)
