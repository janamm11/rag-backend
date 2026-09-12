import pymupdf
from fastapi import APIRouter, UploadFile, File, HTTPException, Form
from langchain_text_splitters import RecursiveCharacterTextSplitter
from typing import Literal
from google import genai
import os

from app.qdrant_client import qdrant_client
from qdrant_client.models import PointStruct
import uuid

from app.mysql_client import mysql_connection
from dotenv import load_dotenv

load_dotenv()

client = genai.Client(api_key= os.getenv("GEMINI_API_KEY"))

router = APIRouter()

def clean_text(text: str) -> str: # thus we preserve the line boundaries while clearing unnecessary whitespace
    lines = [line.strip() for line in text.splitlines()]
    text = "\n".join(line for line in lines if line)
    return text

def fixed_chunk(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]: # used maanuall function
    chunks = []

    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)

        start = end - overlap

    return chunks

def recursive_chunk(text: str) -> list[str]: # used library for recursive chunking
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )

    return splitter.split_text(text)

def generate_embeddings(chunks: list[str]) -> list[list[float]]:
    embeddings = []

    for chunk in chunks:
        result = client.models.embed_content(
            model="gemini-embedding-001",
            contents=chunk
        )

        embeddings.append(result.embeddings[0].values)

    return embeddings


@router.post("/documents/upload")
async def upload_document(file: UploadFile = File(...),
                          strategy: Literal["fixed", "recursive"] = Form("fixed")):

    if not file.filename.endswith((".pdf", ".txt")):
        raise HTTPException(
            status_code=400,
            detail="Only PDF and TXT files are allowed"
        )

    if file.filename.endswith(".pdf"):
        contents = await file.read()
        pdf = pymupdf.open(stream=contents, filetype="pdf")

        text = ""

        for page in pdf:
            text += page.get_text()

        pdf.close()

    else:
        contents = await file.read()
        text = contents.decode("utf-8")

    text = clean_text(text)

    if strategy == "fixed":
        chunks = fixed_chunk(text)

    else: 
        chunks = recursive_chunk(text)

    embeddings = generate_embeddings(chunks)


    points = []

    for chunk, embedding in zip(chunks, embeddings):
        points.append(
            PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload={
                    "text": chunk,
                    "filename": file.filename
                }
            )
        )

    qdrant_client.upsert(
        collection_name="documents",
        points=points
    )


    cursor = mysql_connection.cursor()

    cursor.execute(
    """
    INSERT INTO documents
    (filename, file_type, chunking_strategy, chunk_count)
    VALUES (%s, %s, %s, %s)
    """,
    (
        file.filename,
        file.filename.split(".")[-1].lower(),
        strategy,
        len(chunks),
        ),
    )

    mysql_connection.commit()
    cursor.close()

    return {
        "filename": file.filename,
        "chunk_count": len(chunks),
        "chunks": chunks,
        "embedding_count": len(embeddings),
        "first_embedding": embeddings[0][:5]
       }