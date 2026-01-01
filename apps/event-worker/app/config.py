from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://localhost:5432/artwall"

    # GCP
    gcp_project_id: str = "artwall-project"
    pubsub_subscription: str = "activity-events-sub"

    # CLIP Service
    clip_service_url: str = "http://localhost:8080"

    # Embedding update settings
    activity_weight_view: float = 1.0
    activity_weight_zoom: float = 2.0
    activity_weight_share: float = 3.0
    activity_weight_save: float = 4.0
    activity_weight_purchase: float = 5.0

    # Learning rate for embedding updates
    embedding_learning_rate: float = 0.1

    class Config:
        env_file = ".env"


settings = Settings()


# Activity weights mapping
ACTIVITY_WEIGHTS = {
    "view": settings.activity_weight_view,
    "zoom": settings.activity_weight_zoom,
    "share": settings.activity_weight_share,
    "save": settings.activity_weight_save,
    "purchase": settings.activity_weight_purchase,
}
