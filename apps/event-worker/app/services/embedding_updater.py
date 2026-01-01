import numpy as np
from typing import List, Dict, Any, Optional
import requests

from app.config import settings, ACTIVITY_WEIGHTS
from app.services.database import DatabaseService


class EmbeddingUpdater:
    """Service for updating user embeddings based on activities."""

    def __init__(self, db: DatabaseService):
        self.db = db
        self.learning_rate = settings.embedding_learning_rate

    def process_activities(self, activities: List[Dict[str, Any]]) -> int:
        """Process a batch of activities and update user embeddings."""
        if not activities:
            return 0

        # Group activities by visitor
        activities_by_visitor: Dict[str, List[Dict[str, Any]]] = {}
        for activity in activities:
            visitor_id = activity["visitor_id"]
            if visitor_id not in activities_by_visitor:
                activities_by_visitor[visitor_id] = []
            activities_by_visitor[visitor_id].append(activity)

        processed_count = 0
        processed_ids = []

        for visitor_id, visitor_activities in activities_by_visitor.items():
            try:
                self._update_visitor_embedding(visitor_id, visitor_activities)
                processed_ids.extend([a["id"] for a in visitor_activities])
                processed_count += len(visitor_activities)
            except Exception as e:
                print(f"Error processing activities for visitor {visitor_id}: {e}")

        # Mark processed activities
        if processed_ids:
            self.db.mark_activities_processed(processed_ids)

        return processed_count

    def _update_visitor_embedding(
        self,
        visitor_id: str,
        activities: List[Dict[str, Any]]
    ):
        """Update a single visitor's embedding based on their activities."""
        # Get current user preference
        user_pref = self.db.get_user_preference(visitor_id)

        if user_pref and user_pref.get("embedding"):
            current_embedding = np.array(user_pref["embedding"])
        else:
            # Start with zero vector
            current_embedding = np.zeros(512)

        # Calculate weighted update from activities
        update_vector = np.zeros(512)
        total_weight = 0.0

        for activity in activities:
            event_type = activity["event"]
            weight = ACTIVITY_WEIGHTS.get(event_type, 1.0)

            # Adjust weight based on duration for view events
            if event_type == "view" and activity.get("duration"):
                # Boost weight for longer views (cap at 3x)
                duration_multiplier = min(activity["duration"] / 5000, 3.0)
                weight *= duration_multiplier

            painting_embedding = activity.get("painting_embedding")
            if painting_embedding is not None:
                embedding = np.array(painting_embedding)
                update_vector += weight * embedding
                total_weight += weight

        if total_weight > 0:
            # Normalize update vector
            update_vector = update_vector / total_weight

            # Apply exponential moving average update
            if np.linalg.norm(current_embedding) > 0:
                new_embedding = (
                    (1 - self.learning_rate) * current_embedding +
                    self.learning_rate * update_vector
                )
            else:
                new_embedding = update_vector

            # Normalize to unit vector
            norm = np.linalg.norm(new_embedding)
            if norm > 0:
                new_embedding = new_embedding / norm

            # Update database
            if user_pref:
                self.db.update_user_embedding(
                    visitor_id,
                    new_embedding,
                    increment_count=len(activities)
                )
            else:
                self.db.create_user_preference(visitor_id, new_embedding)

    def get_clip_embedding(self, image_url: str) -> Optional[np.ndarray]:
        """Fetch embedding from CLIP service."""
        try:
            response = requests.post(
                f"{settings.clip_service_url}/api/embedding",
                json={"imageUrl": image_url},
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            return np.array(data["embedding"])
        except Exception as e:
            print(f"Error fetching embedding: {e}")
            return None
