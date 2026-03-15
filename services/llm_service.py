import os
import json
import uuid
import json
from sqlalchemy.orm import Session
from openai import AsyncOpenAI
from models import Chunk, Question, DifficultyLevel
from fastapi import HTTPException
from pydantic import BaseModel
from typing import List, Optional

client = AsyncOpenAI(api_key=os.getenv("LLM_API_KEY"))

# We define the expected LLM output format via Pydantic
class LLMQuestion(BaseModel):
    question: str
    type: str # "MCQ", "True / False", "Fill in the blank"
    options: Optional[List[str]] = None
    answer: str
    difficulty: str # "easy", "medium", "hard"

class LLMResponse(BaseModel):
    questions: List[LLMQuestion]

async def generate_questions_for_document(db: Session, document_id: str):
    chunks = db.query(Chunk).filter(Chunk.document_id == document_id).all()
    
    if not chunks:
        return 0
        
    total_questions_generated = 0
    
    for chunk in chunks:
        # Check if we already have questions for this chunk
        existing = db.query(Question).filter(Question.chunk_id == chunk.id).count()
        if existing > 0:
            continue
            
        system_prompt = """
        You are an expert educational content creator. Your task is to extract quiz questions from the provided educational text content.
        For each piece of text, generate 2-3 questions of varying difficulty.
        The questions should be a mix of MCQ, True / False, and Fill in the blank.
        For MCQ, provide 4 options.
        For True / False, provide options ["True", "False"].
        For Fill in the blank, options can be null or empty, and answer should be the exact word(s).
        Difficulty levels should be strictly 'easy', 'medium', or 'hard'.
        """
        
        user_prompt = f"Topic: {chunk.topic}\nGrade: {chunk.grade}\nSubject: {chunk.subject}\n\nContent:\n{chunk.text}"
        
        try:
            # Using Structured Outputs (JSON Mode with pydantic)
            response = await client.beta.chat.completions.parse(
                model="gpt-4o-2024-08-06",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format=LLMResponse,
            )
            
            result = response.choices[0].message.parsed
            
            for index, q in enumerate(result.questions):
                # Validate enums
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
            # Depending on how strict we want to be, we could skip/log or fail
            print(f"Error generating for chunk {chunk.id}: {str(e)}")
            continue
            
    return total_questions_generated
