import os

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

load_dotenv()

qdrant_client = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY")
)

def create_collection():
    qdrant_client.create_collection(
        collection_name="documents",
        vectors_config=VectorParams(
            size=3072,
            distance=Distance.COSINE
        )
    )