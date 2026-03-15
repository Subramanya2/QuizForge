from pydantic import BaseModel
from typing import List, Optional
from models import DifficultyLevel, QuestionType

# ── Quiz Question Response ──────────────────────────────────────────────────

class QuestionResponse(BaseModel):
    id: str
    question: str
    type: str
    options: Optional[List[str]] = None
    difficulty: str
    quality_score: Optional[int] = None
    source_chunk_id: str

    class Config:
        orm_mode = True

# ── Answer Submission ───────────────────────────────────────────────────────

class AnswerSubmit(BaseModel):
    student_id: str
    question_id: str
    selected_answer: str

# ── API Response Models ─────────────────────────────────────────────────────

class IngestResponse(BaseModel):
    document_id: str
    total_chunks: int

class GenerateResponse(BaseModel):
    document_id: str
    questions_generated: int

class QuizResponse(BaseModel):
    questions: List[QuestionResponse]

class AnswerResponse(BaseModel):
    correct: bool
    correct_answer: str
    new_difficulty: str
