from __future__ import annotations

from typing import Protocol


class QuestionLike(Protocol):
    id: str
    subject: str
    topic: str
    prompt: str
    options: dict[str, str]
    answer: str
    explanation: str
    source_notes: str
    validation_notes: str
