import io
import json
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)


def test_full_flow():
    sample = Path("samples/devops_fundamentals.json").read_bytes()
    import_resp = client.post("/admin/import", files={"file": ("exam.json", io.BytesIO(sample), "application/json")})
    assert import_resp.status_code == 200

    exams = client.get("/admin/exams").json()
    assert any(e["exam_id"] == "exam001" for e in exams)

    start = client.post("/admin/exams/exam001/start", json={"candidate_id": "cand-1"})
    assert start.status_code == 200
    session_id = start.json()["session_id"]

    exam = client.get(f"/candidate/sessions/{session_id}/exam")
    assert exam.status_code == 200
    questions = exam.json()["questions"]

    q_single = next(q for q in questions if q["type"] == "mcq_single")
    q_multi = next(q for q in questions if q["type"] == "mcq_multiple")

    assert client.post(f"/candidate/sessions/{session_id}/answers", json={"question_id": q_single["id"], "answer": "443"}).status_code == 200
    assert client.post(f"/candidate/sessions/{session_id}/answers", json={"question_id": q_multi["id"], "answer": ["Terraform", "Ansible"]}).status_code == 200
    assert client.post(f"/proctor/sessions/{session_id}/events", json={"event_type": "tab_switch", "severity": "high", "details": {"count": 1}}).status_code == 200

    submit = client.post(f"/candidate/sessions/{session_id}/submit")
    assert submit.status_code == 200
    assert submit.json()["status"] == "submitted"
    assert submit.json()["score"] >= 3

    result = client.get(f"/admin/sessions/{session_id}/results")
    assert result.status_code == 200
    assert "answers" in result.json()

    export = client.get(f"/admin/sessions/{session_id}/export")
    assert export.status_code == 200


def test_start_session_rejects_empty_candidate_id():
    sample = Path("samples/devops_fundamentals.json").read_bytes()
    client.post("/admin/import", files={"file": ("exam.json", io.BytesIO(sample), "application/json")})
    resp = client.post("/admin/exams/exam001/start", json={"candidate_id": "   "})
    assert resp.status_code == 422
