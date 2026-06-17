from __future__ import annotations

import json
import os
from datetime import date

from openai import OpenAI

from .generator_types import QuestionLike


QUESTION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "questions": {
            "type": "array",
            "minItems": 30,
            "maxItems": 30,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "id": {"type": "string"},
                    "subject": {"type": "string"},
                    "topic": {"type": "string"},
                    "prompt": {"type": "string"},
                    "options": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "A": {"type": "string"},
                            "B": {"type": "string"},
                            "C": {"type": "string"},
                            "D": {"type": "string"},
                            "E": {"type": "string"}
                        },
                        "required": ["A", "B", "C", "D", "E"]
                    },
                    "answer": {"type": "string", "enum": ["A", "B", "C", "D", "E"]},
                    "explanation": {"type": "string"},
                    "source_notes": {"type": "string"}
                },
                "required": ["id", "subject", "topic", "prompt", "options", "answer", "explanation", "source_notes"]
            }
        }
    },
    "required": ["questions"]
}

VALIDATED_QUESTION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "questions": {
            "type": "array",
            "minItems": 30,
            "maxItems": 30,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "id": {"type": "string"},
                    "subject": {"type": "string"},
                    "topic": {"type": "string"},
                    "prompt": {"type": "string"},
                    "options": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "A": {"type": "string"},
                            "B": {"type": "string"},
                            "C": {"type": "string"},
                            "D": {"type": "string"},
                            "E": {"type": "string"}
                        },
                        "required": ["A", "B", "C", "D", "E"]
                    },
                    "answer": {"type": "string", "enum": ["A", "B", "C", "D", "E"]},
                    "explanation": {"type": "string"},
                    "source_notes": {"type": "string"},
                    "validation_notes": {"type": "string"}
                },
                "required": ["id", "subject", "topic", "prompt", "options", "answer", "explanation", "source_notes", "validation_notes"]
            }
        }
    },
    "required": ["questions"]
}


def generate_questions_with_openai(day: date, source_context: str, subject_plan: dict[str, int]) -> list[QuestionLike]:
    from .generator import Question

    client = OpenAI()
    model = os.getenv("OPENAI_MODEL", "gpt-5-mini")
    plan = ", ".join(f"{subject}: {count}" for subject, count in subject_plan.items())

    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "system",
                "content": (
                    "Voce e um elaborador pedagogico especialista no vestibular Unesp/Vunesp. "
                    "Crie questoes autorais em portugues brasileiro, sem copiar enunciados, imagens, "
                    "alternativas ou textos das provas originais. Use as provas anteriores apenas para "
                    "inferir estilo, topicos, nivel, habilidades cobradas e formato."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Data do simulado: {day.isoformat()}.\n"
                    f"Monte exatamente 30 questoes de multipla escolha para candidata de Odontologia em Sao Jose dos Campos.\n"
                    f"Distribuicao obrigatoria: {plan}.\n"
                    "As questoes devem ter cinco alternativas A-E, uma resposta correta e resolucao comentada curta.\n"
                    "Inclua em source_notes uma descricao breve do padrao real usado, por exemplo: "
                    "'analogia com cobranca recorrente de genetica em 1a fase'.\n\n"
                    f"Contexto extraido/pesquisado das provas anteriores:\n{source_context}"
                ),
            },
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "unesp_daily_exam",
                "strict": True,
                "schema": QUESTION_SCHEMA,
            },
            "verbosity": "low",
        },
        reasoning={"effort": "low"},
    )

    payload = json.loads(response.output_text)
    return [Question(**item) for item in payload["questions"]]


def validate_questions_with_openai(questions: list[QuestionLike]) -> list[QuestionLike]:
    from .generator import Question

    client = OpenAI()
    model = os.getenv("OPENAI_VALIDATOR_MODEL", os.getenv("OPENAI_MODEL", "gpt-5-mini"))
    question_payload = [question.__dict__ for question in questions]

    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "system",
                "content": (
                    "Voce e um corretor rigoroso de vestibular. Confira cada questao de multipla escolha "
                    "antes de liberar o gabarito. Verifique se a alternativa marcada realmente resolve o "
                    "enunciado. Se a resposta salva estiver errada, corrija a letra e reescreva a explicacao. "
                    "Nao altere enunciado nem alternativas."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Revise estas 30 questoes antes da geracao do PDF de respostas. "
                    "Retorne as mesmas questoes, mantendo id, materia, topico, enunciado e alternativas. "
                    "Atualize apenas answer, explanation e validation_notes quando necessario. "
                    "Em validation_notes, informe se a resposta foi confirmada ou corrigida e o motivo curto.\n\n"
                    f"{json.dumps(question_payload, ensure_ascii=False)}"
                ),
            },
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "unesp_validated_answers",
                "strict": True,
                "schema": VALIDATED_QUESTION_SCHEMA,
            },
            "verbosity": "low",
        },
        reasoning={"effort": "medium"},
    )

    payload = json.loads(response.output_text)
    return [Question(**item) for item in payload["questions"]]
