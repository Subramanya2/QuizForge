from fastapi import FastAPI, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from typing import List, Optional
from cachetools import TTLCache
import json

from database import engine, Base, get_db
import models, schemas

# ── DB setup ───────────────────────────────────────────────────────────────

Base.metadata.create_all(bind=engine)

# Auto-migrate: add new nullable columns to the questions table if they don't
# exist yet (handles existing SQLite DBs created before this version).
def _run_migrations():
    with engine.connect() as conn:
        existing = {row[1] for row in conn.execute(text("PRAGMA table_info(questions)"))}
        if "quality_score" not in existing:
            conn.execute(text("ALTER TABLE questions ADD COLUMN quality_score INTEGER"))
        if "embedding" not in existing:
            conn.execute(text("ALTER TABLE questions ADD COLUMN embedding TEXT"))
        conn.commit()

_run_migrations()

# ── FastAPI app ────────────────────────────────────────────────────────────

app = FastAPI(title="QuizForge API", description="AI Content Ingestion + Adaptive Quiz Engine")

# ── Cache: TTL-based in-memory cache for GET /quiz ────────────────────────
# Key: (topic, difficulty, limit)  |  TTL: 5 minutes
_quiz_cache: TTLCache = TTLCache(maxsize=256, ttl=300)


# ── Routes ─────────────────────────────────────────────────────────────────

@app.get("/")
def health_check():
    return {"status": "ok", "message": "QuizForge API is running"}


@app.post("/ingest", response_model=schemas.IngestResponse)
async def ingest_endpoint(
    file: UploadFile = File(...),
    grade: Optional[int] = Form(None),
    subject: Optional[str] = Form(None),
    topic: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    from services.pdf_service import ingest_pdf
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

    # Invalidate all quiz cache entries when new questions are generated
    _quiz_cache.clear()

    return {"document_id": document_id, "questions_generated": questions_count}


@app.get("/quiz", response_model=schemas.QuizResponse)
def get_quiz_endpoint(
    topic: Optional[str] = None,
    difficulty: Optional[models.DifficultyLevel] = None,
    limit: int = 5,
    db: Session = Depends(get_db)
):
    # ── Cache lookup ──────────────────────────────────────────────────────
    cache_key = (topic, difficulty, limit)
    if cache_key in _quiz_cache:
        return _quiz_cache[cache_key]

    # ── Query ─────────────────────────────────────────────────────────────
    query = db.query(models.Question)

    if difficulty:
        query = query.filter(models.Question.difficulty == difficulty)
    if topic:
        query = query.join(models.Chunk).filter(models.Chunk.topic.ilike(f"%{topic}%"))

    questions = query.order_by(func.random()).limit(limit).all()

    response_data = []
    for q in questions:
        options = json.loads(q.options) if q.options else []
        response_data.append(schemas.QuestionResponse(
            id=q.id,
            question=q.question_text,
            type=q.question_type.value,
            options=options,
            difficulty=q.difficulty.value,
            source_chunk_id=q.chunk_id
        ))

    result = {"questions": response_data}

    # ── Cache store ───────────────────────────────────────────────────────
    _quiz_cache[cache_key] = result
    return result


@app.post("/submit-answer", response_model=schemas.AnswerResponse)
def submit_answer_endpoint(
    submission: schemas.AnswerSubmit,
    db: Session = Depends(get_db)
):
    from services.quiz_service import process_student_answer
    return process_student_answer(db, submission)
