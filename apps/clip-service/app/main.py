from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from app.services.embedding import EmbeddingService

app = FastAPI(title="ArtWall CLIP Service", version="1.0.0")

# Initialize embedding service
embedding_service = EmbeddingService()


class ImageRequest(BaseModel):
    imageUrl: str


class BatchImageRequest(BaseModel):
    images: List[dict]  # [{"id": "1", "imageUrl": "..."}]


class EmbeddingResponse(BaseModel):
    embedding: List[float]
    dimensions: int


class BatchEmbeddingResponse(BaseModel):
    results: List[dict]  # [{"id": "1", "embedding": [...]}]


@app.get("/health")
async def health():
    return {"status": "healthy", "model": "ViT-B/32"}


@app.post("/api/embedding", response_model=EmbeddingResponse)
async def get_embedding(request: ImageRequest):
    """Generate embedding for a single image."""
    try:
        embedding = await embedding_service.get_embedding_from_url(request.imageUrl)
        return EmbeddingResponse(
            embedding=embedding,
            dimensions=len(embedding)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/embedding/batch", response_model=BatchEmbeddingResponse)
async def get_batch_embeddings(request: BatchImageRequest):
    """Generate embeddings for multiple images."""
    results = []

    for item in request.images:
        try:
            image_id = item.get("id")
            image_url = item.get("imageUrl")

            if not image_id or not image_url:
                results.append({
                    "id": image_id,
                    "error": "Missing id or imageUrl"
                })
                continue

            embedding = await embedding_service.get_embedding_from_url(image_url)
            results.append({
                "id": image_id,
                "embedding": embedding
            })
        except Exception as e:
            results.append({
                "id": item.get("id"),
                "error": str(e)
            })

    return BatchEmbeddingResponse(results=results)


class FileRequest(BaseModel):
    filePath: str


class BatchFileRequest(BaseModel):
    files: List[dict]  # [{"id": "1", "filePath": "..."}]


@app.post("/api/embedding/file", response_model=EmbeddingResponse)
async def get_embedding_from_file(request: FileRequest):
    """Generate embedding from a local file path."""
    try:
        embedding = embedding_service.get_embedding_from_file(request.filePath)
        return EmbeddingResponse(
            embedding=embedding,
            dimensions=len(embedding)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/embedding/file/batch", response_model=BatchEmbeddingResponse)
async def get_batch_embeddings_from_files(request: BatchFileRequest):
    """Generate embeddings for multiple local files."""
    results = []

    for item in request.files:
        try:
            file_id = item.get("id")
            file_path = item.get("filePath")

            if not file_id or not file_path:
                results.append({
                    "id": file_id,
                    "error": "Missing id or filePath"
                })
                continue

            embedding = embedding_service.get_embedding_from_file(file_path)
            results.append({
                "id": file_id,
                "embedding": embedding
            })
        except Exception as e:
            results.append({
                "id": item.get("id"),
                "error": str(e)
            })

    return BatchEmbeddingResponse(results=results)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
