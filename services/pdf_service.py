import os
import uuid
import tempfile
from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session
from pypdf import PdfReader
from models import Document, Chunk
import re

async def ingest_pdf(db: Session, file: UploadFile, grade: int = None, subject: str = None, topic: str = None):
    # Ensure it's a valid pdf
    content = await file.read()
    
    # generate a unique doc id
    doc_id = f"SRC_{uuid.uuid4().hex[:6].upper()}"
    
    # Save temporarily to read with pypdf
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(content)
        tmp_path = tmp.name
        
    try:
        reader = PdfReader(tmp_path)
        full_text = ""
        for page in reader.pages:
            text = page.extract_text()
            if text:
                full_text += text + "\n"
    except Exception as e:
        os.unlink(tmp_path)
        raise HTTPException(status_code=500, detail=f"Failed to read PDF: {str(e)}")
        
    os.unlink(tmp_path)
    
    # Clean text
    full_text = re.sub(r'\s+', ' ', full_text).strip()
    
    if not full_text:
        raise HTTPException(status_code=400, detail="Could not extract text from PDF")
    
    # Create Document record
    db_doc = Document(id=doc_id, filename=file.filename)
    db.add(db_doc)
    
    # Intelligent Chunking: 
    # Let's split by sentences or small paragraphs (approx 500 characters)
    # A simple approach is split by period and group.
    sentences = re.split(r'(?<=[.!?]) +', full_text)
    
    chunks = []
    current_chunk = ""
    chunk_index = 1
    
    for sentence in sentences:
        if len(current_chunk) + len(sentence) > 600:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence + " "
        else:
            current_chunk += sentence + " "
            
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
        
    for i, text_chunk in enumerate(chunks):
        chunk_id = f"{doc_id}_CH_{i+1:02d}"
        db_chunk = Chunk(
            id=chunk_id,
            document_id=doc_id,
            grade=grade,
            subject=subject,
            topic=topic or file.filename.replace('.pdf', ''),
            text=text_chunk
        )
        db.add(db_chunk)
        
    db.commit()
    return doc_id, len(chunks)
