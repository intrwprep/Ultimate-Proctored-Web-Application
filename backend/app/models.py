from datetime import datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .db import Base


class Exam(Base):
    __tablename__ = "exams"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    payload_hash = Column(String, nullable=False)
    signature_valid = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    questions = relationship("Question", back_populates="exam", cascade="all,delete")


class Question(Base):
    __tablename__ = "questions"

    id = Column(String, primary_key=True)
    exam_id = Column(String, ForeignKey("exams.id"), nullable=False, index=True)
    qtype = Column(String, nullable=False)
    question_text = Column(Text, nullable=False)
    options = Column(JSON, nullable=True)
    correct_answer = Column(JSON, nullable=True)
    marks = Column(Integer, nullable=False)
    difficulty = Column(String, default="medium")
    tags = Column(JSON, default=list)
    time_limit_seconds = Column(Integer, nullable=True)
    image_path = Column(String, nullable=True)
    max_words = Column(Integer, nullable=True)

    exam = relationship("Exam", back_populates="questions")


class ExamSession(Base):
    __tablename__ = "exam_sessions"

    id = Column(String, primary_key=True)
    exam_id = Column(String, ForeignKey("exams.id"), nullable=False)
    candidate_id = Column(String, nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    ends_at = Column(DateTime, nullable=False)
    random_seed = Column(String, nullable=False)
    status = Column(String, default="active")
    submitted_at = Column(DateTime, nullable=True)
    score = Column(Float, nullable=True)


class Answer(Base):
    __tablename__ = "answers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("exam_sessions.id"), index=True)
    question_id = Column(String, ForeignKey("questions.id"), index=True)
    encrypted_answer = Column(Text, nullable=False)
    iv = Column(String, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow)


class ProctorEvent(Base):
    __tablename__ = "proctor_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("exam_sessions.id"), index=True)
    event_type = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    details = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    actor = Column(String, nullable=False)
    action = Column(String, nullable=False)
    object_type = Column(String, nullable=False)
    object_id = Column(String, nullable=False)
    digest = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
