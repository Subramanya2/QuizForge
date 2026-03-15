from pydantic import BaseModel, Field
from typing import List, Optional
from models import DifficultyLevel, QuestionType

# Chunk Schemas
class ChunkBase(BaseModel):
    grade: Optional[int] = None
    subject: Optional[str] = None
    topic: Optional[str] = None
    text: str

class ChunkCreate(ChunkBase):
    id: str  # e.g., SRC_001_CH_01
    document_id: str

class ChunkSchema(ChunkBase):
    id: str
    class Config:
        orm_mode = True

# Question Schemas
class QuestionBase(BaseModel):
    question_text: str = Field(alias="question")
    question_type: QuestionType = Field(alias="type")
    options: Optional[List[str]] = None
    answer: str
    difficulty: DifficultyLevel

class QuestionCreate(QuestionBase):
    id: str
    chunk_id: str
    
    # We will need a way to deal with the `options` since it comes as List[str] but saved as JSON string
    @classmethod
    def from_llm_json(cls, data: dict, q_id: str, chunk_id: str):
        return cls(
            id=q_id,
            chunk_id=chunk_id,
            question=data.get("question"),
            type=data.get("type"),
            options=data.get("options"),
            answer=data.get("answer"),
            difficulty=data.get("difficulty")
        )

class QuestionResponse(BaseModel):
    id: str
    question: str
    type: str # Map from enum
    options: Optional[List[str]] = None
    difficulty: str
    source_chunk_id: str

    class Config:
        orm_mode = True

# Answer Submission
class AnswerSubmit(BaseModel):
    student_id: str
    question_id: str
    selected_answer: str

# API Responses
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
