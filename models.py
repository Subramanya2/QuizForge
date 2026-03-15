from sqlalchemy import Column, Integer, String, Text, ForeignKey, Enum, Float
from sqlalchemy.orm import relationship
import enum
from database import Base

class DifficultyLevel(str, enum.Enum):
    easy = "easy"
    medium = "medium"
    hard = "hard"

class QuestionType(str, enum.Enum):
    mcq = "MCQ"
    tf = "True / False"
    fitb = "Fill in the blank"

class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, index=True) # e.g. SRC_001
    filename = Column(String, index=True)
    chunks = relationship("Chunk", back_populates="document", cascade="all, delete-orphan")

class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(String, primary_key=True, index=True) # e.g. SRC_001_CH_01
    document_id = Column(String, ForeignKey("documents.id"))
    grade = Column(Integer, nullable=True)
    subject = Column(String, nullable=True)
    topic = Column(String, index=True, nullable=True)
    text = Column(Text)

    document = relationship("Document", back_populates="chunks")
    questions = relationship("Question", back_populates="chunk", cascade="all, delete-orphan")

class Question(Base):
    __tablename__ = "questions"

    id = Column(String, primary_key=True, index=True)
    chunk_id = Column(String, ForeignKey("chunks.id"))
    question_text = Column(Text)
    question_type = Column(Enum(QuestionType))
    options = Column(Text, nullable=True) # JSON dumped list for MCQ
    answer = Column(String)
    difficulty = Column(Enum(DifficultyLevel))

    chunk = relationship("Chunk", back_populates="questions")

class StudentProgress(Base):
    __tablename__ = "student_progress"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    student_id = Column(String, index=True)
    topic = Column(String, index=True)
    current_difficulty = Column(Enum(DifficultyLevel), default=DifficultyLevel.easy)
    consecutive_correct = Column(Integer, default=0)

class StudentAnswer(Base):
    __tablename__ = "student_answers"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    student_id = Column(String, index=True)
    question_id = Column(String, ForeignKey("questions.id"))
    selected_answer = Column(String)
    is_correct = Column(Integer) # 1 for true, 0 for false
