# Ultimate Proctored Web Application (Offline, Local-Only)

A complete local-first proctored examination platform supporting MCQ + written answers, proctoring evidence capture, anti-cheating controls, admin/proctor/candidate UIs, and SQLite-backed encrypted storage.

## Full System Architecture
- **Frontend**: Browser-based SPA-style pages:
  - `/` Admin console (`frontend/admin.html`)
  - `/candidate?session_id=<id>` Candidate exam UI (`frontend/candidate.html`)
  - `/proctor?session_id=<id>` Proctor monitor (`frontend/proctor.html`)
- **Backend**: FastAPI (`backend/app/main.py`)
- **Database**: SQLite `exam_local.db`
- **Media/Evidence**: Local filesystem (`backend/media/` exports)
- **Security**: encrypted answers (Fernet), HMAC-signed question file support, SHA-256 tamper hash, audit logs

## Supported Question Types
1. `mcq_single`
2. `mcq_multiple`
3. `short_answer`
4. `essay`

Each question supports `marks`, `difficulty`, `tags`, optional `time_limit_seconds`, optional `image`, optional `max_words`.

## JSON Schema
Canonical schema: `schemas/exam.schema.json`

Example JSON: `samples/devops_fundamentals.json`

## Database Schema
Tables in `backend/app/models.py`:
- `exams`
- `questions`
- `exam_sessions`
- `answers`
- `proctor_events`
- `audit_logs`

## REST API Endpoints
### Admin
- `POST /admin/import`
- `GET /admin/exams`
- `POST /admin/exams/{exam_id}/start`
- `GET /admin/sessions`
- `GET /admin/sessions/{session_id}/results`
- `GET /admin/sessions/{session_id}/export`
- `GET /admin/audit`

### Candidate
- `GET /candidate/sessions/{session_id}/exam`
- `POST /candidate/sessions/{session_id}/answers`
- `POST /candidate/sessions/{session_id}/submit`

### Proctor
- `POST /proctor/sessions/{session_id}/events`
- `GET /proctor/sessions/{session_id}/events`

### Health
- `GET /health`

## UI Wireframes (Implemented)
### Candidate Interface
- Countdown timer
- Question navigator
- MCQ single and multi select
- Essay/short answer text editor
- Fullscreen trigger + event logging
- Autosave on change
- Local webcam/mic monitoring hooks

### Proctor Interface
- Session watcher
- Live event stream
- Critical/high alert rail
- Local preview camera stream

### Admin Interface
- Upload JSON exam
- Start session for candidate
- View sessions and scores
- View audit logs
- Export results/evidence JSON

## Anti-Cheating Mechanisms (Implemented)
- Fullscreen status and exit detection
- Tab switch and focus loss detection
- Clipboard copy/paste blocking + logging
- DevTools heuristic detection
- Per-session deterministic random question order
- Autosave answer writes
- Webcam/microphone activity hooks
- Screen recording event initiation log
- Proctor event timeline persistence

## Local Deployment
### Option 1: Docker Compose
```bash
docker compose up --build
```

### Option 2: Single command local server
```bash
./run_local.sh
```

App URLs:
- Admin: `http://localhost:8000/`
- Candidate: `http://localhost:8000/candidate?session_id=<id>`
- Proctor: `http://localhost:8000/proctor?session_id=<id>`

## Validation / Test
```bash
python3 -m compileall backend/app
python3 -m pytest tests -q
```

## Minimal Working Project Structure
```text
.
├── backend/
│   ├── app/
│   │   ├── db.py
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   └── security.py
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── admin.html
│   ├── candidate.html
│   ├── proctor.html
│   └── assets/styles.css
├── schemas/exam.schema.json
├── samples/devops_fundamentals.json
├── tests/test_app.py
├── docker-compose.yml
└── run_local.sh
```


## User Manual
Detailed operator instructions are available in `USER_MANUAL.md` for admin, candidate, and proctor workflows, troubleshooting, and security notes.
