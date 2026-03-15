from sqlalchemy.orm import Session
from fastapi import HTTPException
from models import StudentProgress, StudentAnswer, Question, DifficultyLevel
from schemas import AnswerSubmit

def process_student_answer(db: Session, submission: AnswerSubmit):
    # Fetch the question
    question = db.query(Question).filter(Question.id == submission.question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
        
    # Check if correct (case-insensitive for text matching, but might need exact match depending on type)
    # Simple check for now
    is_correct = str(question.answer).strip().lower() == str(submission.selected_answer).strip().lower()
    
    # Track the answer
    student_ans = StudentAnswer(
        student_id=submission.student_id,
        question_id=submission.question_id,
        selected_answer=submission.selected_answer,
        is_correct=1 if is_correct else 0
    )
    db.add(student_ans)
    
    # Adaptive Logic
    # 1. Get or create progress record for this topic
    topic = question.chunk.topic
    progress = db.query(StudentProgress).filter(
        StudentProgress.student_id == submission.student_id,
        StudentProgress.topic == topic
    ).first()
    
    if not progress:
        progress = StudentProgress(
            student_id=submission.student_id,
            topic=topic,
            current_difficulty=DifficultyLevel.easy,
            consecutive_correct=0
        )
        db.add(progress)
    
    # 2. Adjust difficulty
    if is_correct:
        progress.consecutive_correct += 1
        # If 2 correct in a row, increase difficulty
        if progress.consecutive_correct >= 2:
            if progress.current_difficulty == DifficultyLevel.easy:
                progress.current_difficulty = DifficultyLevel.medium
            elif progress.current_difficulty == DifficultyLevel.medium:
                progress.current_difficulty = DifficultyLevel.hard
            # Reset streak after promotion
            progress.consecutive_correct = 0
    else:
        # Incorrect answer
        progress.consecutive_correct = 0
        # Decrease difficulty
        if progress.current_difficulty == DifficultyLevel.hard:
            progress.current_difficulty = DifficultyLevel.medium
        elif progress.current_difficulty == DifficultyLevel.medium:
            progress.current_difficulty = DifficultyLevel.easy
            
    db.commit()
    
    return {
        "correct": is_correct,
        "correct_answer": question.answer,
        "new_difficulty": progress.current_difficulty.value
    }
