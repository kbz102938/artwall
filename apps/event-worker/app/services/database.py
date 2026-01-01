import psycopg2
from psycopg2.extras import RealDictCursor
from pgvector.psycopg2 import register_vector
from typing import List, Optional, Dict, Any
import numpy as np

from app.config import settings


class DatabaseService:
    """Service for database operations with pgvector support."""

    def __init__(self):
        self.conn = None
        self._connect()

    def _connect(self):
        """Establish database connection."""
        self.conn = psycopg2.connect(settings.database_url)
        register_vector(self.conn)

    def _ensure_connection(self):
        """Ensure database connection is alive."""
        if self.conn is None or self.conn.closed:
            self._connect()

    def get_unprocessed_activities(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Fetch unprocessed activities."""
        self._ensure_connection()
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT a.id, a.visitor_id, a.event, a.painting_id, a.metadata,
                       p.embedding as painting_embedding
                FROM activities a
                JOIN paintings p ON a.painting_id = p.id
                WHERE a.processed = false AND p.embedding IS NOT NULL
                ORDER BY a.created_at
                LIMIT %s
            """, (limit,))
            return cur.fetchall()

    def get_user_preference(self, visitor_id: str) -> Optional[Dict[str, Any]]:
        """Get user preference with embedding."""
        self._ensure_connection()
        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT visitor_id, embedding, last_style_codes, interaction_count
                FROM user_preferences
                WHERE visitor_id = %s
            """, (visitor_id,))
            return cur.fetchone()

    def update_user_embedding(
        self,
        visitor_id: str,
        embedding: np.ndarray,
        increment_count: int = 1
    ):
        """Update user preference embedding."""
        self._ensure_connection()
        with self.conn.cursor() as cur:
            cur.execute("""
                UPDATE user_preferences
                SET embedding = %s,
                    interaction_count = interaction_count + %s,
                    updated_at = NOW()
                WHERE visitor_id = %s
            """, (embedding.tolist(), increment_count, visitor_id))
        self.conn.commit()

    def create_user_preference(
        self,
        visitor_id: str,
        embedding: np.ndarray,
        style_codes: List[str] = None
    ):
        """Create new user preference with embedding."""
        self._ensure_connection()
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO user_preferences (visitor_id, embedding, last_style_codes, interaction_count)
                VALUES (%s, %s, %s, 1)
                ON CONFLICT (visitor_id) DO UPDATE
                SET embedding = EXCLUDED.embedding,
                    interaction_count = user_preferences.interaction_count + 1,
                    updated_at = NOW()
            """, (visitor_id, embedding.tolist(), style_codes or []))
        self.conn.commit()

    def mark_activities_processed(self, activity_ids: List[str]):
        """Mark activities as processed."""
        self._ensure_connection()
        with self.conn.cursor() as cur:
            cur.execute("""
                UPDATE activities
                SET processed = true
                WHERE id = ANY(%s)
            """, (activity_ids,))
        self.conn.commit()

    def get_painting_embedding(self, painting_id: str) -> Optional[np.ndarray]:
        """Get painting embedding."""
        self._ensure_connection()
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT embedding FROM paintings WHERE id = %s
            """, (painting_id,))
            result = cur.fetchone()
            if result and result[0]:
                return np.array(result[0])
            return None

    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
