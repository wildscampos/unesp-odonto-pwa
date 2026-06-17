from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

from .generator import generate_exam_pdf


ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"
SCHEDULE_PATH = CONFIG_DIR / "study_schedule.json"

DEFAULT_SCHEDULE = {
    "first_exam_date": "2026-06-16",
    "exam_weekdays": [0, 2, 4],
    "answers_in_app": True,
}


def load_schedule() -> dict[str, object]:
    CONFIG_DIR.mkdir(exist_ok=True)
    if not SCHEDULE_PATH.exists():
        SCHEDULE_PATH.write_text(json.dumps(DEFAULT_SCHEDULE, indent=2), encoding="utf-8")
    with SCHEDULE_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def run_scheduled_day(day: date) -> list[Path]:
    schedule = load_schedule()
    first_exam_date = datetime.strptime(str(schedule["first_exam_date"]), "%Y-%m-%d").date()
    exam_weekdays = [int(value) for value in schedule.get("exam_weekdays", [0, 2, 4])]

    if day < first_exam_date:
        return [Path(f"Nenhuma acao: o ciclo comeca em {first_exam_date.isoformat()}.")]

    if day.weekday() in exam_weekdays:
        return [generate_exam_pdf(day)]

    return [Path(f"Nenhuma acao programada para {day.isoformat()}.")]
