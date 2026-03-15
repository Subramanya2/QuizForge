"""
LLM service using Google Gemini 2.5 Flash.

Features:
  - Structured quiz question generation (MCQ, True/False, Fill in the blank)
  - In-prompt quality evaluation (score 1-10 per question, threshold 7+)
  - Embedding-based semantic deduplication before saving to DB
  - Per-chunk deduplication (skip already-processed chunks)
"""
import os
import json
import uuid
import re
from sqlalchemy.orm import Session
from google import genai
from google.genai import types
from models import Chunk, Question, DifficultyLevel
from fastapi import HTTPException
from typing import List, Optional
from pydantic import BaseModel


# ── Pydantic schemas for LLM output ────────────────────────────────────────

class LLMQuestion(BaseModel):
    question: str
    type: str           # "MCQ" | "True / False" | "Fill in the blank"
    options: Optional[List[str]] = None
    answer: str
    difficulty: str     # "easy" | "medium" | "hard"
    quality_score: int  # 1-10 self-assessed quality score

class LLMResponse(BaseModel):
    questions: List[LLMQuestion]


# ── Helpers ────────────────────────────────────────────────────────────────

def get_gemini_client() -> genai.Client:
    api_key = os.getenv("LLM_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="LLM_API_KEY environment variable is not set")
    return genai.Client(api_key=api_key)

SYSTEM_PROMPT = """You are an expert educational content creator.
Generate 2-3 quiz questions from the provided educational text content.
Mix question types: MCQ, True / False, and Fill in the blank.
- For MCQ: provide exactly 4 options as a JSON array.
- For True / False: options must be ["True", "False"].
- For Fill in the blank: set options to null.
Difficulty must strictly be 'easy', 'medium', or 'hard'.

After generating each question, evaluate its quality (clarity, correctness,
relevance to the source text) on a scale of 1-10 and include it as quality_score.

Return ONLY valid JSON matching this schema (no extra text):
{
  "questions": [
    {
      "question": "...",
      "type": "MCQ",
      "options": ["A", "B", "C", "D"],
      "answer": "A",
      "difficulty": "easy",
      "quality_score": 9
    }
  ]
}"""

QUALITY_THRESHOLD = 7     # Questions scoring below this are rejected
SIMILARITY_THRESHOLD = 0.92  # Cosine similarity above this = duplicate


# ── Main generation function ───────────────────────────────────────────────

async def generate_questions_for_document(db: Session, document_id: str) -> int:
    chunks = db.query(Chunk).filter(Chunk.document_id == document_id).all()

    if not chunks:
        return 0

    client = get_gemini_client()
    total_generated = 0

    # Lazy import to avoid circular deps
    from services.embedding_service import get_embedding, is_semantically_duplicate

    for chunk in chunks:
        # Per-chunk deduplication: skip if already generated
        existing = db.query(Question).filter(Question.chunk_id == chunk.id).count()
        if existing > 0:
            continue

        user_prompt = (
            f"Topic: {chunk.topic}\nGrade: {chunk.grade}\nSubject: {chunk.subject}"
            f"\n\nContent:\n{chunk.text}"
        )

        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    types.Content(
                        role="user",
                        parts=[types.Part(text=SYSTEM_PROMPT + "\n\n" + user_prompt)]
                    )
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )

            raw_text = response.text.strip()
            # Strip markdown fences if Gemini adds them
            raw_text = re.sub(r'^```(?:json)?\s*', '', raw_text)
            raw_text = re.sub(r'\s*```$', '', raw_text)

            data = json.loads(raw_text)
            result = LLMResponse(**data)

        except Exception as e:
            print(f"[LLM] Error for chunk {chunk.id}: {e}")
            continue

        for q in result.questions:
            # ── 1. Quality gate ──────────────────────────────────────────
            if q.quality_score < QUALITY_THRESHOLD:
                print(f"[Quality] Rejected question (score {q.quality_score}): {q.question[:60]}")
                continue

            # ── 2. Normalise type and difficulty ─────────────────────────
            difficulty = q.difficulty.lower()
            if difficulty not in ("easy", "medium", "hard"):
                difficulty = "medium"

            q_type = q.type
            if q_type not in ("MCQ", "True / False", "Fill in the blank"):
                if q.options and len(q.options) == 4:
                    q_type = "MCQ"
                elif q.options and len(q.options) == 2:
                    q_type = "True / False"
                else:
                    q_type = "Fill in the blank"

            # ── 3. Embedding-based semantic deduplication ─────────────────
            embedding_vec = None
            try:
                embedding_vec = get_embedding(client, q.question)
                if is_semantically_duplicate(db, document_id, embedding_vec, SIMILARITY_THRESHOLD):
                    print(f"[Dedup] Skipped duplicate question: {q.question[:60]}")
                    continue
            except Exception as e:
                print(f"[Embedding] Warning — skipping dedup check: {e}")

            # ── 4. Save question ──────────────────────────────────────────
            new_q = Question(
                id=f"Q_{uuid.uuid4().hex[:8]}",
                chunk_id=chunk.id,
                question_text=q.question,
                question_type=q_type,
                options=json.dumps(q.options) if q.options else None,
                answer=q.answer,
                difficulty=DifficultyLevel(difficulty),
                quality_score=q.quality_score,
                embedding=json.dumps(embedding_vec) if embedding_vec else None,
            )
            db.add(new_q)
            total_generated += 1

        db.commit()

    return total_generated
