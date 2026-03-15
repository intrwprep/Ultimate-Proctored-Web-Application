import json
import os
import random
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from jsonschema import ValidationError, validate
from sqlalchemy.orm import Session

from .db import Base, engine, get_db
from .models import Answer, AuditLog, Exam, ExamSession, ProctorEvent, Question
from .schemas import (
    AnswerPayload,
    ProctorEventPayload,
    ProctorEventResponse,
    StartSessionRequest,
    SubmitResponse,
)
from .security import get_fernet, sha256_digest, verify_exam_signature

app = FastAPI(title="Offline Proctored Exam Platform", version="1.0.0")
Base.metadata.create_all(bind=engine)

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "schemas" / "exam.schema.json"
UPLOAD_DIR = ROOT / "backend" / "media"
FRONTEND_DIR = ROOT / "frontend"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
FRONTEND_DIR.mkdir(parents=True, exist_ok=True)

if (FRONTEND_DIR / "assets").exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")


def _read_answers(db: Session, session_id: str) -> list[Answer]:
    return db.query(Answer).filter(Answer.session_id == session_id).all()


def _decrypt_answers(db: Session, session_id: str) -> dict[str, object]:
    fernet = get_fernet()
    payload = {}
    for item in _read_answers(db, session_id):
        payload[item.question_id] = json.loads(fernet.decrypt(item.encrypted_answer.encode()).decode())
    return payload


def _score_session(db: Session, session: ExamSession) -> tuple[float, float]:
    answers = _decrypt_answers(db, session.id)
    questions = db.query(Question).filter(Question.exam_id == session.exam_id).all()
    total = sum(q.marks for q in questions)
    score = 0.0
    for q in questions:
        if q.qtype == "mcq_single":
            if answers.get(q.id) == q.correct_answer:
                score += q.marks
        elif q.qtype == "mcq_multiple":
            expected = set(q.correct_answer or [])
            actual = set(answers.get(q.id, []))
            if expected and actual == expected:
                score += q.marks
    return score, float(total)


@app.get("/")
def root_page():
    return FileResponse(FRONTEND_DIR / "admin.html")


@app.get("/candidate")
def candidate_page():
    return FileResponse(FRONTEND_DIR / "candidate.html")


@app.get("/proctor")
def proctor_page():
    return FileResponse(FRONTEND_DIR / "proctor.html")


@app.get("/health")
def healthcheck():
    return {"status": "ok", "mode": "offline", "time": datetime.utcnow()}


@app.post("/admin/import")
async def import_exam(file: UploadFile = File(...), db: Session = Depends(get_db)):
    raw = await file.read()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {exc}") from exc

    schema = json.loads(SCHEMA_PATH.read_text())
    try:
        validate(payload, schema)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=f"Schema validation error: {exc.message}") from exc

    signature = payload.pop("signature", None)
    signing_secret = os.getenv("EXAM_SIGNING_SECRET", "local-dev-secret")
    signature_valid = verify_exam_signature(payload, signature, signing_secret)
    payload_hash = sha256_digest(json.dumps(payload, sort_keys=True).encode())

    exam = Exam(
        id=payload["exam_id"],
        title=payload["title"],
        duration_minutes=payload["duration_minutes"],
        payload_hash=payload_hash,
        signature_valid=signature_valid,
    )
    db.merge(exam)

    for q in payload["questions"]:
        db.merge(
            Question(
                id=q["id"],
                exam_id=payload["exam_id"],
                qtype=q["type"],
                question_text=q["question"],
                options=q.get("options"),
                correct_answer=q.get("correct_answer"),
                marks=q["marks"],
                difficulty=q.get("difficulty", "medium"),
                tags=q.get("tags", []),
                time_limit_seconds=q.get("time_limit_seconds"),
                image_path=q.get("image"),
                max_words=q.get("max_words"),
            )
        )

    db.add(
        AuditLog(
            actor="admin",
            action="exam_imported",
            object_type="exam",
            object_id=payload["exam_id"],
            digest=payload_hash,
        )
    )
    db.commit()
    return {
        "exam_id": payload["exam_id"],
        "signature_valid": signature_valid,
        "tamper_hash": payload_hash,
        "question_count": len(payload["questions"]),
    }


@app.get("/admin/exams")
def list_exams(db: Session = Depends(get_db)):
    exams = db.query(Exam).all()
    return [{"exam_id": e.id, "title": e.title, "duration_minutes": e.duration_minutes} for e in exams]


@app.post("/admin/exams/{exam_id}/start")
def start_session(exam_id: str, req: StartSessionRequest, db: Session = Depends(get_db)):
    exam = db.get(Exam, exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    now = datetime.utcnow()
    session_id = str(uuid.uuid4())
    seed = str(uuid.uuid4())
    session = ExamSession(
        id=session_id,
        exam_id=exam_id,
        candidate_id=req.candidate_id,
        started_at=now,
        ends_at=now + timedelta(minutes=exam.duration_minutes),
        random_seed=seed,
    )
    db.add(session)
    db.add(AuditLog(actor="admin", action="session_started", object_type="session", object_id=session_id))
    db.commit()
    return {"session_id": session_id, "ends_at": session.ends_at, "status": session.status}


@app.get("/candidate/sessions/{session_id}/exam")
def get_exam_for_candidate(session_id: str, db: Session = Depends(get_db)):
    session = db.get(ExamSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status != "active":
        raise HTTPException(status_code=403, detail="Session closed")

    exam = db.get(Exam, session.exam_id)
    questions = db.query(Question).filter(Question.exam_id == exam.id).all()

    rng = random.Random(session.random_seed)
    rng.shuffle(questions)

    sanitized_questions = [
        {
            "id": q.id,
            "type": q.qtype,
            "question": q.question_text,
            "options": q.options,
            "marks": q.marks,
            "difficulty": q.difficulty,
            "tags": q.tags,
            "time_limit_seconds": q.time_limit_seconds,
            "image": q.image_path,
            "max_words": q.max_words,
        }
        for q in questions
    ]

    return {
        "exam_id": exam.id,
        "title": exam.title,
        "ends_at": session.ends_at,
        "candidate_id": session.candidate_id,
        "questions": sanitized_questions,
    }


@app.post("/candidate/sessions/{session_id}/answers")
def autosave_answer(session_id: str, payload: AnswerPayload, db: Session = Depends(get_db)):
    session = db.get(ExamSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status != "active":
        raise HTTPException(status_code=403, detail="Session closed")

    fernet = get_fernet()
    token = fernet.encrypt(json.dumps(payload.answer).encode()).decode()

    existing = (
        db.query(Answer)
        .filter(Answer.session_id == session_id, Answer.question_id == payload.question_id)
        .first()
    )
    if existing:
        existing.encrypted_answer = token
        existing.updated_at = datetime.utcnow()
    else:
        db.add(
            Answer(
                session_id=session_id,
                question_id=payload.question_id,
                encrypted_answer=token,
                iv="fernet-managed",
            )
        )

    db.add(
        AuditLog(
            actor="candidate",
            action="answer_autosaved",
            object_type="session",
            object_id=session_id,
        )
    )
    db.commit()
    return {"status": "saved", "session_id": session_id, "question_id": payload.question_id}


@app.post("/candidate/sessions/{session_id}/submit", response_model=SubmitResponse)
def submit_session(session_id: str, db: Session = Depends(get_db)):
    session = db.get(ExamSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status != "active":
        raise HTTPException(status_code=400, detail="Session already submitted")

    score, max_score = _score_session(db, session)
    session.status = "submitted"
    session.submitted_at = datetime.utcnow()
    session.score = score
    db.add(AuditLog(actor="candidate", action="session_submitted", object_type="session", object_id=session_id))
    db.commit()
    return {"session_id": session.id, "score": score, "max_score": max_score, "status": session.status}


@app.post("/proctor/sessions/{session_id}/events")
def log_event(session_id: str, payload: ProctorEventPayload, db: Session = Depends(get_db)):
    if not db.get(ExamSession, session_id):
        raise HTTPException(status_code=404, detail="Session not found")

    event = ProctorEvent(
        session_id=session_id,
        event_type=payload.event_type,
        severity=payload.severity,
        details=payload.details,
    )
    db.add(event)
    db.add(
        AuditLog(
            actor="proctor-agent",
            action="proctor_event",
            object_type="session",
            object_id=session_id,
            digest=payload.event_type,
        )
    )
    db.commit()
    return {"status": "logged"}


@app.get("/proctor/sessions/{session_id}/events", response_model=list[ProctorEventResponse])
def list_events(session_id: str, db: Session = Depends(get_db)):
    return db.query(ProctorEvent).filter(ProctorEvent.session_id == session_id).all()


@app.get("/admin/sessions")
def list_sessions(db: Session = Depends(get_db)):
    sessions = db.query(ExamSession).all()
    return [
        {
            "session_id": s.id,
            "exam_id": s.exam_id,
            "candidate_id": s.candidate_id,
            "status": s.status,
            "score": s.score,
            "ends_at": s.ends_at,
        }
        for s in sessions
    ]


@app.get("/admin/sessions/{session_id}/results")
def get_results(session_id: str, db: Session = Depends(get_db)):
    session = db.get(ExamSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    answers = _decrypt_answers(db, session_id)
    events = db.query(ProctorEvent).filter(ProctorEvent.session_id == session_id).all()
    return {
        "session_id": session_id,
        "status": session.status,
        "score": session.score,
        "answers": answers,
        "events": [
            {
                "event_type": e.event_type,
                "severity": e.severity,
                "details": e.details,
                "created_at": e.created_at,
            }
            for e in events
        ],
    }


@app.get("/admin/sessions/{session_id}/export")
def export_results(session_id: str, db: Session = Depends(get_db)):
    report = get_results(session_id, db)
    export_path = UPLOAD_DIR / f"{session_id}_export.json"
    export_path.write_text(json.dumps(report, default=str, indent=2))
    return {"exported_to": str(export_path)}


@app.get("/admin/audit")
def list_audit_logs(db: Session = Depends(get_db)):
    rows = db.query(AuditLog).order_by(AuditLog.created_at.desc()).limit(200).all()
    return [
        {
            "actor": r.actor,
            "action": r.action,
            "object_type": r.object_type,
            "object_id": r.object_id,
            "digest": r.digest,
            "created_at": r.created_at,
        }
        for r in rows
    ]
