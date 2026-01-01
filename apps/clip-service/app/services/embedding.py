import torch
import requests
from PIL import Image
from io import BytesIO
from typing import List
from transformers import CLIPProcessor, CLIPModel


class EmbeddingService:
    """Service for generating CLIP embeddings from images."""

    def __init__(self, model_name: str = "openai/clip-vit-base-patch32"):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = CLIPModel.from_pretrained(model_name).to(self.device)
        self.processor = CLIPProcessor.from_pretrained(model_name)
        self.model.eval()

    def _preprocess_image(self, image: Image.Image) -> torch.Tensor:
        """Preprocess image for CLIP model."""
        inputs = self.processor(images=image, return_tensors="pt")
        return inputs["pixel_values"].to(self.device)

    def get_embedding(self, image: Image.Image) -> List[float]:
        """Generate embedding for a PIL Image."""
        with torch.no_grad():
            pixel_values = self._preprocess_image(image)
            image_features = self.model.get_image_features(pixel_values=pixel_values)
            # Normalize the embedding
            image_features = image_features / image_features.norm(p=2, dim=-1, keepdim=True)
            return image_features.cpu().numpy().flatten().tolist()

    async def get_embedding_from_url(self, url: str) -> List[float]:
        """Fetch image from URL and generate embedding."""
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        image = Image.open(BytesIO(response.content)).convert("RGB")
        return self.get_embedding(image)

    def get_embedding_from_file(self, file_path: str) -> List[float]:
        """Load image from file and generate embedding."""
        image = Image.open(file_path).convert("RGB")
        return self.get_embedding(image)

    def get_text_embedding(self, text: str) -> List[float]:
        """Generate embedding for text (useful for style descriptions)."""
        with torch.no_grad():
            inputs = self.processor(text=[text], return_tensors="pt", padding=True)
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            text_features = self.model.get_text_features(**inputs)
            text_features = text_features / text_features.norm(p=2, dim=-1, keepdim=True)
            return text_features.cpu().numpy().flatten().tolist()

    def get_batch_embeddings(self, images: List[Image.Image]) -> List[List[float]]:
        """Generate embeddings for multiple images in batch."""
        with torch.no_grad():
            inputs = self.processor(images=images, return_tensors="pt", padding=True)
            pixel_values = inputs["pixel_values"].to(self.device)
            image_features = self.model.get_image_features(pixel_values=pixel_values)
            image_features = image_features / image_features.norm(p=2, dim=-1, keepdim=True)
            return image_features.cpu().numpy().tolist()
