from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
import asyncio
from contextlib import asynccontextmanager

from app.config import settings
from app.services.database import DatabaseService
from app.services.embedding_updater import EmbeddingUpdater


# Global services
db_service: Optional[DatabaseService] = None
embedding_updater: Optional[EmbeddingUpdater] = None
processing_task: Optional[asyncio.Task] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    global db_service, embedding_updater, processing_task

    # Startup
    db_service = DatabaseService()
    embedding_updater = EmbeddingUpdater(db_service)

    # Start background processing loop
    processing_task = asyncio.create_task(background_processor())

    yield

    # Shutdown
    if processing_task:
        processing_task.cancel()
        try:
            await processing_task
        except asyncio.CancelledError:
            pass
    if db_service:
        db_service.close()


app = FastAPI(
    title="ArtWall Event Worker",
    version="1.0.0",
    lifespan=lifespan
)


class ActivityEvent(BaseModel):
    """Pub/Sub activity event message."""
    visitorId: str
    event: str
    paintingId: str
    duration: Optional[int] = None
    metadata: Optional[dict] = None


class ProcessResponse(BaseModel):
    processed: int
    message: str


async def background_processor():
    """Background task to continuously process activities."""
    while True:
        try:
            if embedding_updater:
                activities = db_service.get_unprocessed_activities(limit=50)
                if activities:
                    count = embedding_updater.process_activities(activities)
                    print(f"Processed {count} activities")
                await asyncio.sleep(5)  # Poll every 5 seconds
            else:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Error in background processor: {e}")
            await asyncio.sleep(10)  # Wait longer on error


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "service": "event-worker"}


@app.post("/process", response_model=ProcessResponse)
async def process_activities():
    """Manually trigger activity processing."""
    if not embedding_updater or not db_service:
        return ProcessResponse(processed=0, message="Service not initialized")

    activities = db_service.get_unprocessed_activities(limit=100)
    count = embedding_updater.process_activities(activities)

    return ProcessResponse(
        processed=count,
        message=f"Processed {count} activities"
    )


@app.post("/pubsub")
async def handle_pubsub(event: ActivityEvent, background_tasks: BackgroundTasks):
    """
    Handle Pub/Sub push endpoint.
    This can be used as an alternative to pull-based processing.
    """
    # For now, we rely on the background processor
    # This endpoint can be used for real-time push if needed
    return {"status": "received"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081)
