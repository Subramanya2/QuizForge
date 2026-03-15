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

# We define the expected LLM output format via Pydantic
class LLMQuestion(BaseModel):
    question: str
    type: str  # "MCQ", "True / False", "Fill in the blank"
    options: Optional[List[str]] = None
    answer: str
    difficulty: str  # "easy", "medium", "hard"

class LLMResponse(BaseModel):
    questions: List[LLMQuestion]

def get_gemini_client():
    api_key = os.getenv("LLM_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="LLM_API_KEY environment variable is not set")
    return genai.Client(api_key=api_key)

async def generate_questions_for_document(db: Session, document_id: str):
    chunks = db.query(Chunk).filter(Chunk.document_id == document_id).all()

    if not chunks:
        return 0

    total_questions_generated = 0

    for chunk in chunks:
        # Deduplication: skip if we already have questions for this chunk
        existing = db.query(Question).filter(Question.chunk_id == chunk.id).count()
        if existing > 0:
            continue

        system_prompt = """You are an expert educational content creator.
Generate 2-3 quiz questions from the provided educational text content.
Mix question types: MCQ, True / False, and Fill in the blank.
- For MCQ: provide exactly 4 options as a JSON array.
- For True / False: options must be ["True", "False"].
- For Fill in the blank: set options to null.
Difficulty must strictly be 'easy', 'medium', or 'hard'.

Return ONLY valid JSON matching this schema (no extra text):
{
  "questions": [
    {
      "question": "...",
      "type": "MCQ",
      "options": ["A", "B", "C", "D"],
      "answer": "A",
      "difficulty": "easy"
    }
  ]
}"""

        user_prompt = f"Topic: {chunk.topic}\nGrade: {chunk.grade}\nSubject: {chunk.subject}\n\nContent:\n{chunk.text}"

        try:
            client = get_gemini_client()
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    types.Content(role="user", parts=[types.Part(text=system_prompt + "\n\n" + user_prompt)])
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )

            raw_text = response.text.strip()

            # Sometimes Gemini wraps in markdown code fences — strip them
            raw_text = re.sub(r'^```(?:json)?\s*', '', raw_text)
            raw_text = re.sub(r'\s*```$', '', raw_text)

            data = json.loads(raw_text)
            result = LLMResponse(**data)

            for q in result.questions:
                difficulty = q.difficulty.lower()
                if difficulty not in ["easy", "medium", "hard"]:
                    difficulty = "medium"

                q_type = q.type
                if q_type not in ["MCQ", "True / False", "Fill in the blank"]:
                    if q.options and len(q.options) == 4:
                        q_type = "MCQ"
                    elif q.options and len(q.options) == 2:
                        q_type = "True / False"
                    else:
                        q_type = "Fill in the blank"

                options_str = json.dumps(q.options) if q.options else None

                new_q = Question(
                    id=f"Q_{uuid.uuid4().hex[:8]}",
                    chunk_id=chunk.id,
                    question_text=q.question,
                    question_type=q_type,
                    options=options_str,
                    answer=q.answer,
                    difficulty=DifficultyLevel(difficulty)
                )
                db.add(new_q)
                total_questions_generated += 1

            db.commit()

        except Exception as e:
            print(f"Error generating for chunk {chunk.id}: {str(e)}")
            continue

    return total_questions_generated
