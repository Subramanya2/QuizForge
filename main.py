from fastapi import FastAPI, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional

from database import engine, Base, get_db
import models, schemas
import json

Base.metadata.create_all(bind=engine)

app = FastAPI(title="QuizForge API", description="AI Content Ingestion + Adaptive Quiz Engine")

@app.get("/")
def health_check():
    return {"status": "ok", "message": "Peblo API is running"}

@app.post("/ingest", response_model=schemas.IngestResponse)
async def ingest_endpoint(
    file: UploadFile = File(...),
    grade: Optional[int] = Form(None),
    subject: Optional[str] = Form(None),
    topic: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    from services.pdf_service import ingest_pdf
    # In a real app we might read chunk size from config, or run this in a background task
    document_id, chunk_count = await ingest_pdf(db, file, grade, subject, topic)
    
    return {"document_id": document_id, "total_chunks": chunk_count}

@app.post("/generate-quiz", response_model=schemas.GenerateResponse)
async def generate_quiz_endpoint(
    document_id: str,
    db: Session = Depends(get_db)
):
    db_doc = db.query(models.Document).filter(models.Document.id == document_id).first()
    if not db_doc:
        raise HTTPException(status_code=404, detail="Document not found")
        
    from services.llm_service import generate_questions_for_document
    questions_count = await generate_questions_for_document(db, document_id)
    
    return {"document_id": document_id, "questions_generated": questions_count}

@app.get("/quiz", response_model=schemas.QuizResponse)
def get_quiz_endpoint(
    topic: Optional[str] = None,
    difficulty: Optional[models.DifficultyLevel] = None,
    limit: int = 5,
    db: Session = Depends(get_db)
):
    query = db.query(models.Question)
    
    if difficulty:
        query = query.filter(models.Question.difficulty == difficulty)
        
    if topic:
        query = query.join(models.Chunk).filter(models.Chunk.topic.ilike(f"%{topic}%"))
        
    questions = query.order_by(func.random()).limit(limit).all()
    
    response = []
    for q in questions:
        options = json.loads(q.options) if q.options else []
        response.append(schemas.QuestionResponse(
            id=q.id,
            question=q.question_text,
            type=q.question_type.value,
            options=options,
            difficulty=q.difficulty.value,
            source_chunk_id=q.chunk_id
        ))
        
    return {"questions": response}

@app.post("/submit-answer", response_model=schemas.AnswerResponse)
def submit_answer_endpoint(
    submission: schemas.AnswerSubmit,
    db: Session = Depends(get_db)
):
    from services.quiz_service import process_student_answer
    result = process_student_answer(db, submission)
    return result
