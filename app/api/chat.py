import os

import redis
from dotenv import load_dotenv
from fastapi import APIRouter
from pydantic import BaseModel

from google import genai
from app.qdrant_client import qdrant_client

from app.mysql_client import mysql_connection, get_cursor

from datetime import datetime

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

router = APIRouter()

r = redis.Redis(
    host=os.getenv("REDIS_HOST"),
    port=int(os.getenv("REDIS_PORT")),
    decode_responses=True,
    username=os.getenv("REDIS_USERNAME"),
    password=os.getenv("REDIS_PASSWORD"),
)


class ChatRequest(BaseModel):
    session_id: str
    message: str

class Booking(BaseModel):
    is_booking: bool
    name: str | None = None
    email: str | None = None
    interview_date: str | None = None
    interview_time: str | None = None




def search_qdrant(question: str):
    result = client.models.embed_content(
        model="gemini-embedding-001",
        contents=question
    )

    query_embedding = result.embeddings[0].values

    results = qdrant_client.query_points(
        collection_name="documents",
        query=query_embedding,
        limit=3
    )

    return [point.payload["text"] for point in results.points]

def extract_booking(message: str, conversation: str):
    prompt = f"""
Look at the conversation and latest message and determine if the user
is trying to book an interview.

Conversation:
{conversation}

Latest message:
{message}

Return ONLY valid JSON, nothing else, in exactly this format:

{{"is_booking": true or false,
"name": "...",
"email": "...",
"interview_date": "...",
"interview_time": "..."}}

Set is_booking to true if the user is trying to book an interview,
even if some booking information is missing.

Use the conversation to recover information provided in earlier messages.

If any field is missing, use null.

For interview_time, always return 24-hour format HH:MM:SS.
For example, 2pm must be returned as 14:00:00.
"""

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt
    )

    import json
    text = response.text.strip().replace("```json", "").replace("```", "")

    return Booking(**json.loads(text))

def normalize_time(time_text: str) -> str:
    for fmt in ("%H:%M:%S", "%H:%M", "%I:%M %p", "%I %p", "%I%p"):
        try:
            return datetime.strptime(
                time_text.strip().upper(),
                fmt
            ).strftime("%H:%M:%S")
        except ValueError:
            pass

    raise ValueError("Invalid interview time")

def save_booking(booking: Booking, session_id: str):
    interview_time = normalize_time(booking.interview_time)

    cursor = get_cursor()
    cursor.execute(
        "INSERT INTO bookings (session_id, name, email, interview_date, interview_time) VALUES (%s, %s, %s, %s, %s)",
        (
            session_id,
            booking.name,
            booking.email,
            booking.interview_date,
            interview_time
        )
    )
    mysql_connection.commit()
    cursor.close()

@router.post("/chat")
def chat(request: ChatRequest):

    r.rpush(request.session_id, f"User: {request.message}")
    messages = r.lrange(request.session_id, -15, -1)
    r.ltrim(request.session_id, -20, -1)
    conversation = "\n".join(messages)

    booking = extract_booking(request.message, conversation)

    if booking.is_booking:
        if booking.name and booking.email and booking.interview_date and booking.interview_time:
            save_booking(booking, request.session_id)
            answer = f"Got it! Booking confirmed for {booking.name} on {booking.interview_date} at {booking.interview_time}."
        else:
            answer = "I'd love to help you book an interview — could you give me your name, email, preferred date, and time?"
    else:
        chunks = search_qdrant(request.message)
        context = "\n".join(chunks)
        prompt = f"Context from documents:\n{context}\n\nConversation so far:\n{conversation}\n\nAnswer the user's last message using the context above."
        response = client.models.generate_content(model="gemini-3.6-flash", contents=prompt)
        answer = response.text

    r.rpush(request.session_id, f"AI: {answer}")
    r.ltrim(request.session_id, -20, -1)

    return {"session_id": request.session_id, "answer": answer}