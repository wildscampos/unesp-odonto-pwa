from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .schedule import load_schedule


ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = ROOT / "state"
WEB_DATA_DIR = ROOT / "web" / "public" / "data"


def export_web_data() -> Path:
    WEB_DATA_DIR.mkdir(parents=True, exist_ok=True)
    exams = []

    for state_path in sorted(STATE_DIR.glob("prova-*.json")):
        date_text = state_path.stem.replace("prova-", "")
        questions = json.loads(state_path.read_text(encoding="utf-8"))
        exams.append(
            {
                "id": date_text,
                "date": date_text,
                "title": f"Simulado Unesp Odontologia - {format_br_date(date_text)}",
                "questionCount": len(questions),
                "questions": questions,
            }
        )

    payload = {
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "schedule": load_schedule(),
        "exams": exams,
    }

    out_path = WEB_DATA_DIR / "exams.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path


def format_br_date(date_text: str) -> str:
    year, month, day = date_text.split("-")
    return f"{day}/{month}/{year}"
