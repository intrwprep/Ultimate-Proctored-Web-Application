from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, StringConstraints
from typing_extensions import Annotated


NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class StartSessionRequest(BaseModel):
    candidate_id: NonEmptyStr


class AnswerPayload(BaseModel):
    question_id: NonEmptyStr
    answer: Any


class ProctorEventPayload(BaseModel):
    event_type: Literal[
        "tab_switch",
        "focus_loss",
        "fullscreen_exit",
        "copy_attempt",
        "paste_attempt",
        "devtools_suspected",
        "mic_activity",
        "multiple_faces",
        "screen_recording",
        "webcam_snapshot",
    ]
    severity: Literal["low", "medium", "high", "critical"] = "medium"
    details: dict[str, Any] = Field(default_factory=dict)


class ProctorEventResponse(BaseModel):
    event_type: str
    severity: str
    details: dict[str, Any]
    created_at: datetime


class SubmitResponse(BaseModel):
    session_id: str
    score: float
    max_score: float
    status: str
