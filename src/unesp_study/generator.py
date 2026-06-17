from __future__ import annotations

import json
import os
import random
import textwrap
from dataclasses import dataclass
from datetime import date
from importlib.resources import files
from pathlib import Path
from typing import Iterable

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .ai_generator import generate_questions_with_openai, validate_questions_with_openai
from .sources import build_source_context, has_extracted_pdf_text


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / "output"
STATE_DIR = ROOT / "state"

SUBJECT_PLAN = {
    "Biologia": 7,
    "Quimica": 6,
    "Matematica": 4,
    "Fisica": 3,
    "Geografia": 3,
    "Historia": 3,
    "Portugues": 3,
    "Ingles": 1,
}


@dataclass(frozen=True)
class Question:
    id: str
    subject: str
    topic: str
    prompt: str
    options: dict[str, str]
    answer: str
    explanation: str
    source_notes: str = ""
    validation_notes: str = ""


def load_bank() -> list[Question]:
    data_path = files("unesp_study").joinpath("data/question_bank.json")
    with data_path.open("r", encoding="utf-8") as file:
        raw_questions = json.load(file)
    return [Question(**item) for item in raw_questions]


def select_questions(day: date, bank: list[Question]) -> list[Question]:
    rng = random.Random(day.isoformat())
    selected: list[Question] = []

    for subject, count in SUBJECT_PLAN.items():
        candidates = [question for question in bank if question.subject == subject]
        if len(candidates) < count:
            raise ValueError(f"Banco insuficiente para {subject}: {len(candidates)} de {count}.")
        selected.extend(rng.sample(candidates, count))

    rng.shuffle(selected)
    return selected[:30]


def generate_exam_pdf(day: date) -> Path:
    questions = build_daily_questions(day)
    OUTPUT_DIR.mkdir(exist_ok=True)
    STATE_DIR.mkdir(exist_ok=True)

    state_path = STATE_DIR / f"prova-{day.isoformat()}.json"
    with state_path.open("w", encoding="utf-8") as file:
        json.dump([question.__dict__ for question in questions], file, ensure_ascii=False, indent=2)

    pdf_path = OUTPUT_DIR / f"prova-unesp-odontologia-{day.isoformat()}.pdf"
    build_exam_pdf(pdf_path, day, questions)
    return pdf_path


def build_daily_questions(day: date) -> list[Question]:
    source_context = build_source_context()
    if os.getenv("OPENAI_API_KEY") and source_context and has_extracted_pdf_text():
        return generate_questions_with_openai(day, source_context, SUBJECT_PLAN)
    return select_questions(day, load_bank())


def generate_answers_pdf(day: date) -> Path:
    state_path = STATE_DIR / f"prova-{day.isoformat()}.json"
    if not state_path.exists():
        return Path(f"Resolucao nao criada: nao existe prova salva para {day.isoformat()}.")

    with state_path.open("r", encoding="utf-8") as file:
        questions = [Question(**item) for item in json.load(file)]

    questions = validate_answers_before_pdf(questions)
    with state_path.open("w", encoding="utf-8") as file:
        json.dump([question.__dict__ for question in questions], file, ensure_ascii=False, indent=2)

    OUTPUT_DIR.mkdir(exist_ok=True)
    pdf_path = OUTPUT_DIR / f"resolucao-unesp-odontologia-{day.isoformat()}.pdf"
    build_answers_pdf(pdf_path, day, questions)
    return pdf_path


def validate_answers_before_pdf(questions: list[Question]) -> list[Question]:
    structurally_validated = [validate_question_structure(question) for question in questions]
    if os.getenv("OPENAI_API_KEY"):
        return validate_questions_with_openai(structurally_validated)
    return structurally_validated


def validate_question_structure(question: Question) -> Question:
    expected_letters = {"A", "B", "C", "D", "E"}
    option_letters = set(question.options)
    if option_letters != expected_letters:
        missing = ", ".join(sorted(expected_letters - option_letters))
        extra = ", ".join(sorted(option_letters - expected_letters))
        raise ValueError(f"Questao {question.id} com alternativas invalidas. Faltando: {missing}. Extras: {extra}.")
    if question.answer not in expected_letters:
        raise ValueError(f"Questao {question.id} com resposta invalida: {question.answer}.")
    if not question.options[question.answer].strip():
        raise ValueError(f"Questao {question.id} tem alternativa correta vazia.")

    notes = question.validation_notes or "Validacao estrutural concluida antes da resolucao."
    return Question(**{**question.__dict__, "validation_notes": notes})


def base_doc(path: Path) -> SimpleDocTemplate:
    return SimpleDocTemplate(
        str(path),
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.4 * cm,
        bottomMargin=1.4 * cm,
    )


def styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("Title", parent=base["Title"], fontName="Helvetica-Bold", fontSize=16, leading=20),
        "subtitle": ParagraphStyle("Subtitle", parent=base["Normal"], fontSize=9, leading=12, textColor=colors.HexColor("#555555")),
        "question": ParagraphStyle("Question", parent=base["Normal"], fontSize=10, leading=14, spaceAfter=5),
        "option": ParagraphStyle("Option", parent=base["Normal"], fontSize=9.5, leading=13, leftIndent=10),
        "small": ParagraphStyle("Small", parent=base["Normal"], fontSize=8, leading=10, textColor=colors.HexColor("#666666")),
    }


def build_exam_pdf(path: Path, day: date, questions: Iterable[Question]) -> None:
    st = styles()
    story = [
        Paragraph("Prova diaria - Unesp Odontologia", st["title"]),
        Paragraph(f"Data: {day.strftime('%d/%m/%Y')} | 30 questoes | Tempo sugerido: 2h30", st["subtitle"]),
        Spacer(1, 0.25 * cm),
        Paragraph("Questões autorais baseadas em padrões de provas anteriores da Unesp/Vunesp. Marque uma alternativa por questao.", st["small"]),
        Spacer(1, 0.35 * cm),
    ]

    for index, question in enumerate(questions, start=1):
        story.append(Paragraph(f"<b>{index}. [{question.subject}]</b> {escape(question.prompt)}", st["question"]))
        for letter in ["A", "B", "C", "D", "E"]:
            story.append(Paragraph(f"{letter}) {escape(question.options[letter])}", st["option"]))
        story.append(Spacer(1, 0.25 * cm))

    base_doc(path).build(story)


def build_answers_pdf(path: Path, day: date, questions: list[Question]) -> None:
    st = styles()
    rows = [["Questao", "Materia", "Resposta"]]
    rows.extend([[str(index), question.subject, question.answer] for index, question in enumerate(questions, start=1)])

    table = Table(rows, colWidths=[2 * cm, 6 * cm, 3 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EEF7")),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#BBBBBB")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ]
        )
    )

    story = [
        Paragraph("Resolucao comentada - Unesp Odontologia", st["title"]),
        Paragraph(f"Prova de {day.strftime('%d/%m/%Y')}", st["subtitle"]),
        Spacer(1, 0.3 * cm),
        table,
        PageBreak(),
    ]

    for index, question in enumerate(questions, start=1):
        story.append(Paragraph(f"<b>{index}. [{question.subject} - {question.topic}] Resposta: {question.answer}</b>", st["question"]))
        story.append(Paragraph(escape(wrap_explanation(question.explanation)), st["option"]))
        if question.validation_notes:
            story.append(Paragraph(f"Conferencia: {escape(question.validation_notes)}", st["small"]))
        if question.source_notes:
            story.append(Paragraph(f"Base de estilo/conteudo: {escape(question.source_notes)}", st["small"]))
        story.append(Spacer(1, 0.25 * cm))

    base_doc(path).build(story)


def wrap_explanation(text: str) -> str:
    return "\n".join(textwrap.wrap(text, width=110))


def escape(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
