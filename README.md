# Peblo AI Backend Engine

This repository contains the backend system for Peblo AI, a platform that ingests educational content from PDFs, processes it, and generates an adaptive quiz engine using LLM.

## Architecture

The system is built using:
- **FastAPI** for high-performance API endpoints.
- **SQLite + SQLAlchemy** for relational, structured storage of documents, chunks, questions, and student progress.
- **OpenAI (gpt-4o)** for structured generating of quizzes using Pydantic schema validation.
- **PyPDF** for intelligent sentence-based chunking of educational PDFs.

## Setup Instructions

### 1. Requirements

Make sure you have Python 3.9+ installed.

### 2. Installation

1. Clone or copy the files into a directory.
2. It's recommended to create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### 3. Environment Variables

Create a `.env` file in the root of the project with your OpenAI API key and Database URI. You can copy the template:
```bash
cp .env.example .env
```
Inside `.env`, set:
```
LLM_API_KEY=your_actual_openai_api_key_here
DATABASE_URL=sqlite:///./peblo.db
```

### 4. Running the Backend

Start the FastAPI server using Uvicorn:
```bash
uvicorn main:app --reload
```

The server will be available at `http://127.0.0.1:8000`.

### 5. API Testing (Swagger docs)

FastAPI provides an automatic, interactive API documentation.
Open your browser and navigate to:
[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

From here, you can execute all the endpoints.

## Examples of Usage

1. **Ingest a PDF**
   - Use `POST /ingest`
   - Upload any of the provided PDFs (e.g. `peblo_pdf_grade4_english_grammar.pdf`).
   - Returns a `document_id`.

2. **Generate Questions**
   - Use `POST /generate-quiz`
   - Pass the `document_id`.
   - The LLM will process the chunks and generate MCQs, True/False, and Fill In The Blank questions.

3. **Fetch Quiz**
   - Use `GET /quiz`
   - You can fetch by `topic` (e.g., "grammar") or `difficulty` ("easy", "medium", "hard").

4. **Submit Answer (Adaptive Logic)**
   - Use `POST /submit-answer`
   - Send:
     ```json
     {
       "student_id": "S001",
       "question_id": "Q_XXXXXX",
       "selected_answer": "False"
     }
     ```
   - The system tracks consecutive correct/incorrect answers to automatically adjust the student's difficulty level for the next questions.
