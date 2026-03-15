"""
Embedding service: generates text embeddings via Gemini and checks cosine 
similarity to detect semantically duplicate questions before saving them.
"""
import json
import math
from google import genai
from sqlalchemy.orm import Session
from models import Question


def get_embedding(client: genai.Client, text: str) -> list[float]:
    """Generate a text embedding using Gemini text-embedding-004."""
    response = client.models.embed_content(
        model="models/text-embedding-004",
        contents=text
    )
    return response.embeddings[0].values


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(a * b for a, b in zip(v1, v2))
    mag1 = math.sqrt(sum(a * a for a in v1))
    mag2 = math.sqrt(sum(b * b for b in v2))
    if mag1 == 0 or mag2 == 0:
        return 0.0
    return dot / (mag1 * mag2)


def is_semantically_duplicate(
    db: Session,
    document_id: str,
    new_embedding: list[float],
    threshold: float = 0.92
) -> bool:
    """
    Check if a question with a similar embedding already exists for the document.
    Returns True if a near-duplicate is found (similarity > threshold).
    """
    # Fetch all questions for this document that have embeddings
    from models import Chunk
    existing_questions = (
        db.query(Question)
        .join(Chunk, Question.chunk_id == Chunk.id)
        .filter(Chunk.document_id == document_id)
        .filter(Question.embedding.isnot(None))
        .all()
    )

    for q in existing_questions:
        existing_embedding = json.loads(q.embedding)
        similarity = cosine_similarity(new_embedding, existing_embedding)
        if similarity > threshold:
            return True

    return False
