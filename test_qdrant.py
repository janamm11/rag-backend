# from app.qdrant_client import qdrant_client, create_collection

# create_collection()

# print(qdrant_client.get_collections())

from app.qdrant_client import qdrant_client

result = qdrant_client.count(
    collection_name="documents"
)

print("Points stored:", result.count)