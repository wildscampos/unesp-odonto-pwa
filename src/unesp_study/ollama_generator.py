from __future__ import annotations

import json
import os
import random
import re
import time
import urllib.error
import urllib.request
from datetime import date
from importlib.resources import files
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
            try:
                payload = generate_single_question_payload(
                    model=model,
                    day=day,
                    subject=subject,
                    index=index,
                    count=count,
                    source_context=source_context,
                )
            except Exception as exc:
                print(f"[ollama] Geracao de {subject} {index}/{count} falhou; usando fallback local: {exc}")
                payload = fallback_question_payload(day=day, subject=subject, index=index)
            questions.extend(Question(**{**item, "subject": subject}) for item in payload["questions"])

    random.Random(day.isoformat()).shuffle(questions)
    return questions


def validate_questions_with_ollama(questions: list[QuestionLike]) -> list[QuestionLike]:
    from .generator import Question

    model = current_validator_model()
    validated: list[Question] = []

    for index, question in enumerate(questions, start=1):
        try:
            payload = validate_single_question_payload(model=model, question=question, index=index, total=len(questions))
            validated.append(Question(**payload["questions"][0]))
        except Exception as exc:
            print(f"[ollama] Validacao da questao {index} falhou apos retentativas: {exc}")
            notes = "Validacao estrutural mantida; Ollama local nao retornou JSON valido apos retentativas."
            validated.append(Question(**{**question.__dict__, "validation_notes": notes}))

    return validated


def generate_single_question_payload(
    model: str,
    day: date,
    subject: str,
    index: int,
    count: int,
    source_context: str,
) -> dict[str, Any]:
    messages = [
        {
            "role": "system",
            "content": (
                "/no_think\n"
                "Voce e um elaborador pedagogico especialista no vestibular Unesp/Vunesp. "
                "Responda somente com JSON valido, sem markdown. Crie questao autoral em portugues brasileiro, "
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
                "Retorne apenas um objeto JSON compacto neste formato: "
                '{"questions":[{"id":"...","subject":"...","topic":"...","prompt":"...",'
                '"options":{"A":"...","B":"...","C":"...","D":"...","E":"..."},'
                '"answer":"A","explanation":"...","source_notes":"..."}]}.\n'
                "Nao inclua markdown, comentarios, texto fora do JSON, nem blocos de raciocinio.\n\n"
                f"Contexto extraido/pesquisado das provas anteriores:\n{source_context}"
            ),
        },
    ]
    return request_payload_with_retries(
        model=model,
        schema=question_schema(1),
        messages=messages,
        expected_count=1,
        label=f"geracao {subject} {index}/{count}",
    )


def validate_single_question_payload(model: str, question: QuestionLike, index: int, total: int) -> dict[str, Any]:
    messages = [
        {
            "role": "system",
            "content": (
                "/no_think\n"
                "Voce e um corretor rigoroso de vestibular. Responda somente com JSON valido, sem markdown. "
                "Confira se a alternativa marcada realmente resolve o enunciado. "
                "Se a resposta estiver errada, corrija answer e explanation. "
                "Nao altere enunciado, alternativas, materia, topico ou id."
            ),
        },
        {
            "role": "user",
            "content": (
                "/no_think\n"
                f"Revise a questao {index} de {total}. "
                "Retorne exatamente 1 questao, atualizando apenas answer, explanation e validation_notes quando necessario. "
                "Em validation_notes, informe se a resposta foi confirmada ou corrigida e o motivo curto.\n\n"
                f"{json.dumps({'questions': [question.__dict__]}, ensure_ascii=False)}"
            ),
        },
    ]
    return request_payload_with_retries(
        model=model,
        schema=validated_question_schema(1),
        messages=messages,
        expected_count=1,
        require_validation_notes=True,
        label=f"validacao {index}/{total}",
    )


def request_payload_with_retries(
    model: str,
    messages: list[dict[str, str]],
    schema: dict[str, Any],
    expected_count: int,
    label: str,
    require_validation_notes: bool = False,
) -> dict[str, Any]:
    attempts = int(os.getenv("OLLAMA_JSON_RETRIES", "4"))
    last_error: Exception | None = None

    for attempt in range(1, attempts + 1):
        try:
            content = chat_json(model=model, schema=schema, messages=messages)
            payload = parse_payload(content)
            validate_payload_shape(payload, expected_count=expected_count, require_validation_notes=require_validation_notes)
            if attempt > 1:
                print(f"[ollama] {label}: sucesso na tentativa {attempt}.")
            return payload
        except Exception as exc:
            last_error = exc
            print(f"[ollama] {label}: tentativa {attempt}/{attempts} falhou: {exc}")
            if attempt < attempts:
                time.sleep(min(2 * attempt, 8))

    raise RuntimeError(f"{label} falhou apos {attempts} tentativas.") from last_error


def fallback_question_payload(day: date, subject: str, index: int) -> dict[str, Any]:
    data_path = files("unesp_study").joinpath("data/question_bank.json")
    with data_path.open("r", encoding="utf-8") as file:
        bank = json.load(file)

    candidates = [item for item in bank if item.get("subject") == subject]
    if not candidates:
        raise ValueError(f"Banco local sem questoes de fallback para {subject}.")

    selected = random.Random(f"{day.isoformat()}-{subject}-{index}").choice(candidates)
    question = {
        **selected,
        "id": f"local-fallback-{day.isoformat()}-{slug(subject)}-{index:02d}",
        "source_notes": (
            "Fallback local usado porque o Ollama nao retornou JSON valido apos retentativas. "
            "Questao do banco autoral interno inspirado em padroes Unesp/Vunesp."
        ),
    }
    return {"questions": [question]}


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
    cleaned = clean_model_content(content)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as first_error:
        extracted = extract_first_json_object(cleaned)
        repaired = repair_common_json_issues(extracted)
        try:
            return json.loads(repaired)
        except json.JSONDecodeError as second_error:
            raise ValueError(
                f"JSON invalido retornado pelo Ollama: {second_error.msg} na linha {second_error.lineno}, coluna {second_error.colno}."
            ) from first_error


def clean_model_content(content: str) -> str:
    cleaned = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL | re.IGNORECASE).strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def extract_first_json_object(content: str) -> str:
    start = content.find("{")
    if start == -1:
        raise ValueError("Ollama nao retornou objeto JSON.")

    depth = 0
    in_string = False
    escaped = False
    for position in range(start, len(content)):
        char = content[position]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return content[start : position + 1]

    raise ValueError("Ollama retornou JSON incompleto.")


def repair_common_json_issues(content: str) -> str:
    repaired = content.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    repaired = re.sub(r",\s*([}\]])", r"\1", repaired)
    return repaired


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
