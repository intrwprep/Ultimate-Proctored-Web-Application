# Ultimate Proctored Web Application — User Manual

This manual explains how to run and operate the offline proctored exam system.

## 1. Quick Start

### Option A: Docker (recommended)
```bash
docker compose up --build
```

### Option B: Local Python
```bash
./run_local.sh
```

### Option C: VS Code task runner
1. Open project in VS Code.
2. Press `Ctrl+Shift+P` → **Tasks: Run Task**.
3. Choose **Install deps & Start Proctored App**.

This runs `scripts/vscode_bootstrap.sh`, which creates `.venv`, installs dependencies, and starts Uvicorn in reload mode.

Open:
- Admin console: `http://localhost:8000/`
- Candidate console: `http://localhost:8000/candidate?session_id=<session-id>`
- Proctor console: `http://localhost:8000/proctor?session_id=<session-id>`

---

## 2. Roles and Workflow

### Admin (Exam Coordinator)
1. Open Admin console.
2. Import an exam JSON file.
3. Select exam + enter candidate ID.
4. Click **Start Session**.
5. Share candidate and proctor URLs.
6. After completion, review sessions and export results.

### Candidate (Exam Taker)
1. Open candidate URL received from admin.
2. Allow camera and microphone permissions.
3. Stay in fullscreen mode during exam.
4. Answer questions (answers autosave).
5. Click **Submit Exam** when finished.

### Proctor (Supervisor)
1. Open proctor URL from admin.
2. Enter session ID (or prefilled from URL).
3. Click **Watch**.
4. Monitor event timeline and critical alerts.

---

## 3. JSON Exam File Requirements

Required top-level fields:
- `exam_id`
- `title`
- `duration_minutes`
- `questions` (array)

Supported question types:
- `mcq_single`
- `mcq_multiple`
- `short_answer`
- `essay`

Recommended per-question fields:
- `id`, `type`, `question`, `marks`
- Optional: `difficulty`, `tags`, `time_limit_seconds`, `image`, `max_words`

Reference schema:
- `schemas/exam.schema.json`

Sample file:
- `samples/devops_fundamentals.json`

---

## 4. Anti-Cheating Signals Captured

The candidate page logs and sends local events for:
- Tab switch / focus loss
- Fullscreen exit
- Copy/paste attempts
- DevTools heuristic trigger
- Microphone activity spikes
- Webcam snapshot triggers
- Placeholder multi-face detection events
- Local recording start indicator

All events are available in proctor view and included in exports.

---

## 5. Results and Evidence Export

Admin can export per session via:
- **Sessions → export** link
- API endpoint: `/admin/sessions/{session_id}/export`

Export includes:
- session metadata
- decrypted submitted answers
- proctoring event timeline

---

## 6. Troubleshooting

### "Import failed"
- Ensure JSON is valid and follows `schemas/exam.schema.json`.

### Candidate cannot start exam
- Verify session ID exists and session is active.

### No webcam/mic feed
- Candidate/proctor must allow browser media permissions.

### Proctor sees no events
- Confirm correct session ID.
- Candidate must have loaded exam page and generated interactions.

### Port already in use
- Stop existing process using port 8000, then restart app.

---

## 7. Security Notes

- Answers are encrypted before storage.
- Exam payload hash is stored for tamper evidence.
- Optional HMAC signature can be validated during import.
- Audit log records admin, candidate, and proctor actions.

