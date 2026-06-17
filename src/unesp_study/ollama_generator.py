from __future__ import annotations

import json
import os
import random
import re
import urllib.error
import urllib.request
from datetime import date
from typing import Any

from .generator_types import QuestionLike


OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:4b")


def question_schema(expected_count: int) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "questions": {
                "type": "array",
                "minItems": expected_count,
                "maxItems": expected_count,
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "subject": {"type": "string"},
                        "topic": {"type": "string"},
                        "prompt": {"type": "string"},
                        "options": {
                            "type": "object",
                            "properties": {
                                "A": {"type": "string"},
                                "B": {"type": "string"},
                                "C": {"type": "string"},
                                "D": {"type": "string"},
                                "E": {"type": "string"},
                            },
                            "required": ["A", "B", "C", "D", "E"],
                        },
                        "answer": {"type": "string", "enum": ["A", "B", "C", "D", "E"]},
                        "explanation": {"type": "string"},
                        "source_notes": {"type": "string"},
                    },
                    "required": ["id", "subject", "topic", "prompt", "options", "answer", "explanation", "source_notes"],
                },
            }
        },
        "required": ["questions"],
    }


def validated_question_schema(expected_count: int) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "questions": {
                "type": "array",
                "minItems": expected_count,
                "maxItems": expected_count,
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "subject": {"type": "string"},
                        "topic": {"type": "string"},
                        "prompt": {"type": "string"},
                        "options": {
                            "type": "object",
                            "properties": {
                                "A": {"type": "string"},
                                "B": {"type": "string"},
                                "C": {"type": "string"},
                                "D": {"type": "string"},
                                "E": {"type": "string"},
                            },
                            "required": ["A", "B", "C", "D", "E"],
                        },
                        "answer": {"type": "string", "enum": ["A", "B", "C", "D", "E"]},
                        "explanation": {"type": "string"},
                        "source_notes": {"type": "string"},
                        "validation_notes": {"type": "string"},
                    },
                    "required": [
                        "id",
                        "subject",
                        "topic",
                        "prompt",
                        "options",
                        "answer",
                        "explanation",
                        "source_notes",
                        "validation_notes",
                    ],
                },
            }
        },
        "required": ["questions"],
    }


def generate_questions_with_ollama(day: date, source_context: str, subject_plan: dict[str, int]) -> list[QuestionLike]:
    from .generator import Question

    model = current_model()
    questions: list[Question] = []

    for subject, count in subject_plan.items():
        for index in range(1, count + 1):
            content = chat_json(
                model=model,
                schema=question_schema(1),
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "/no_think\n"
                            "Voce e um elaborador pedagogico especialista no vestibular Unesp/Vunesp. "
                            "Responda somente com JSON valido. Crie questao autoral em portugues brasileiro, "
                            "sem copiar enunciados, imagens, alternativas ou textos das provas originais. "
                            "Use as provas anteriores apenas para inferir estilo, topicos, nivel e formato."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            "/no_think\n"
                            f"Data do simulado: {day.isoformat()}.\n"
                            f"Monte exatamente 1 questao de {subject} para candidata de Odontologia em Sao Jose dos Campos.\n"
                            f"Esta e a questao {index} de {count} de {subject}; varie o topico dentro da materia.\n"
                            "A questao deve ter alternativas A, B, C, D e E, uma unica resposta correta, "
                            "explicacao curta e source_notes descrevendo o padrao real usado.\n"
                            f"Use id unico no formato local-{day.isoformat()}-{slug(subject)}-{index:02d}.\n"
                            "Nao inclua markdown, comentarios, texto fora do JSON, nem blocos de raciocinio.\n\n"
                            f"Contexto extraido/pesquisado das provas anteriores:\n{source_context}"
                        ),
                    },
                ],
            )
            payload = parse_payload(content)
            validate_payload_shape(payload, expected_count=1)
            questions.extend(Question(**{**item, "subject": subject}) for item in payload["questions"])

    random.Random(day.isoformat()).shuffle(questions)
    return questions


def validate_questions_with_ollama(questions: list[QuestionLike]) -> list[QuestionLike]:
    from .generator import Question

    model = current_validator_model()
    question_payload = [question.__dict__ for question in questions]
    content = chat_json(
        model=model,
        schema=validated_question_schema(len(questions)),
        messages=[
            {
                "role": "system",
                "content": (
                    "/no_think\n"
                    "Voce e um corretor rigoroso de vestibular. Responda somente com JSON valido. "
                    "Confira se a alternativa marcada realmente resolve cada enunciado. "
                    "Se a resposta estiver errada, corrija answer e explanation. "
                    "Nao altere enunciado, alternativas, materia, topico ou id."
                ),
            },
            {
                "role": "user",
                "content": (
                    "/no_think\n"
                    "Revise estas 30 questoes antes da publicacao. "
                    "Retorne as mesmas questoes, atualizando apenas answer, explanation e validation_notes quando necessario. "
                    "Em validation_notes, informe se a resposta foi confirmada ou corrigida e o motivo curto.\n\n"
                    f"{json.dumps(question_payload, ensure_ascii=False)}"
                ),
            },
        ],
    )
    payload = parse_payload(content)
    validate_payload_shape(payload, expected_count=len(questions), require_validation_notes=True)
    return [Question(**item) for item in payload["questions"]]


def current_model() -> str:
    return os.getenv("OLLAMA_MODEL", DEFAULT_MODEL)


def current_validator_model() -> str:
    return os.getenv("OLLAMA_VALIDATOR_MODEL", os.getenv("OLLAMA_MODEL", DEFAULT_MODEL))


def chat_json(model: str, messages: list[dict[str, str]], schema: dict[str, Any]) -> str:
    body = {
        "model": model,
        "stream": False,
        "messages": messages,
        "format": schema,
        "think": False,
        "options": {
            "temperature": 0.25,
            "top_p": 0.9,
            "num_ctx": int(os.getenv("OLLAMA_NUM_CTX", "4096")),
            "num_predict": int(os.getenv("OLLAMA_NUM_PREDICT", "900")),
        },
    }
    request = urllib.request.Request(
        f"{OLLAMA_URL.rstrip('/')}/api/chat",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "900"))) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Ollama nao respondeu em {OLLAMA_URL}. Instale/inicie o Ollama e baixe o modelo {model}."
        ) from exc
    return str(result.get("message", {}).get("content", ""))


def parse_payload(content: str) -> dict[str, Any]:
    cleaned = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL | re.IGNORECASE).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        return json.loads(cleaned[start : end + 1])


def validate_payload_shape(payload: dict[str, Any], expected_count: int, require_validation_notes: bool = False) -> None:
    questions = payload.get("questions")
    if not isinstance(questions, list) or len(questions) != expected_count:
        raise ValueError(f"Ollama retornou {len(questions) if isinstance(questions, list) else 0} questoes; esperado: {expected_count}.")

    expected_letters = {"A", "B", "C", "D", "E"}
    for item in questions:
        if set(item.get("options", {})) != expected_letters:
            raise ValueError(f"Questao {item.get('id', '?')} com alternativas invalidas.")
        if item.get("answer") not in expected_letters:
            raise ValueError(f"Questao {item.get('id', '?')} com resposta invalida.")
        if require_validation_notes and not item.get("validation_notes"):
            raise ValueError(f"Questao {item.get('id', '?')} sem validation_notes.")


def slug(value: str) -> str:
    replacements = {
        "á": "a",
        "à": "a",
        "ã": "a",
        "â": "a",
        "é": "e",
        "ê": "e",
        "í": "i",
        "ó": "o",
        "ô": "o",
        "õ": "o",
        "ú": "u",
        "ç": "c",
    }
    text = value.lower()
    for source, target in replacements.items():
        text = text.replace(source, target)
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")
