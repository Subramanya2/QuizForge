# Peblo AI Backend Engine

A backend system that ingests educational PDF content, generates AI-powered quiz questions using Google Gemini, and serves them through an adaptive quiz API.

## Architecture

- **FastAPI** — high-performance REST API endpoints
- **SQLite + SQLAlchemy** — structured storage for documents, chunks, questions, and student progress
- **Google Gemini 2.5 Flash** — LLM for structured quiz question generation (MCQ, True/False, Fill in the blank)
- **PyPDF** — intelligent sentence-based text extraction and chunking from PDFs

## Project Structure

```
peblo_backend/
├── services/
│   ├── llm_service.py      # Gemini integration + question generation
│   ├── pdf_service.py      # PDF parsing + chunking
│   └── quiz_service.py     # Adaptive difficulty logic
├── .env.example            # Environment variable template
├── database.py             # SQLAlchemy engine + session
├── main.py                 # FastAPI app + route definitions
├── models.py               # SQLAlchemy ORM models
├── requirements.txt
└── schemas.py              # Pydantic request/response schemas
```

## Database Schema

| Table              | Description                                      |
|--------------------|--------------------------------------------------|
| `documents`        | Ingested PDF source files                        |
| `chunks`           | Extracted, cleaned text segments per document   |
| `questions`        | AI-generated quiz questions linked to chunks     |
| `student_progress` | Per-student difficulty tracking per topic        |
| `student_answers`  | Full history of student answer submissions       |

## Setup Instructions

### 1. Requirements

Python 3.9+ required.

### 2. Installation

```bash
# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Variables

```bash
cp .env.example .env
```

Edit `.env` and set your Google Gemini API key:

```
LLM_API_KEY=your_google_gemini_api_key_here
DATABASE_URL=sqlite:///./peblo.db
```

Get a free Gemini API key at [aistudio.google.com](https://aistudio.google.com/apikey).

### 4. Running the Server

```bash
uvicorn main:app --reload
```

Server runs at `http://127.0.0.1:8000`

### 5. Interactive API Docs (Swagger)

Open `http://127.0.0.1:8000/docs` to explore and test all endpoints.

---

## API Endpoints

### `POST /ingest`
Upload a PDF to extract and store its content.

**Form fields:**
- `file` — PDF file (required)
- `grade` — Grade level (optional, e.g. `3`)
- `subject` — Subject name (optional, e.g. `Science`)
- `topic` — Topic label (optional, e.g. `Photosynthesis`)

**Response:**
```json
{ "document_id": "SRC_ABC123", "total_chunks": 4 }
```

---

### `POST /generate-quiz`
Generate quiz questions from an ingested document using Gemini.

**Query param:** `document_id=SRC_ABC123`

**Response:**
```json
{ "document_id": "SRC_ABC123", "questions_generated": 12 }
```

> Duplicate detection is built in — re-running on the same document will not generate duplicate questions.

---

### `GET /quiz`
Retrieve quiz questions filtered by topic and/or difficulty.

**Query params:** `topic`, `difficulty` (`easy`/`medium`/`hard`), `limit` (default: 5)

**Response:**
```json
{
  "questions": [
    {
      "id": "Q_a1b2c3d4",
      "question": "What is photosynthesis?",
      "type": "MCQ",
      "options": ["Process A", "Process B", "Process C", "Process D"],
      "difficulty": "easy",
      "source_chunk_id": "SRC_ABC123_CH_01"
    }
  ]
}
```

---

### `POST /submit-answer`
Submit a student answer to trigger adaptive difficulty adjustment.

**Request body:**
```json
{
  "student_id": "S001",
  "question_id": "Q_a1b2c3d4",
  "selected_answer": "Process B"
}
```

**Response:**
```json
{
  "correct": true,
  "correct_answer": "Process B",
  "new_difficulty": "medium"
}
```

---

## Adaptive Difficulty Logic

The system adjusts difficulty per student, per topic:

| Event | Result |
|-------|--------|
| 2 correct answers in a row | Difficulty increases (easy → medium → hard) |
| Any incorrect answer | Difficulty decreases (hard → medium → easy) |

The recommended difficulty for the next question is returned in every `/submit-answer` response.

---

## Sample Test Files

The following PDFs can be ingested (provided by Peblo):
- `peblo_pdf_grade1_math_numbers.pdf` — Grade 1 Math
- `peblo_pdf_grade3_science_plants_animals.pdf` — Grade 3 Science
- `peblo_pdf_grade4_english_grammar.pdf` — Grade 4 English Grammar
