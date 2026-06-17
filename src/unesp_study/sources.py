from __future__ import annotations

import json
import re
from pathlib import Path

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[2]
SOURCES_DIR = ROOT / "sources"
MANIFEST_PATH = SOURCES_DIR / "source_manifest.json"
EXTRACTED_DIR = SOURCES_DIR / "extracted"


def build_source_context(max_chars: int = 24000) -> str:
    SOURCES_DIR.mkdir(exist_ok=True)
    EXTRACTED_DIR.mkdir(exist_ok=True)
    extract_all_pdfs()

    chunks: list[str] = []
    if MANIFEST_PATH.exists():
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        chunks.append("Fontes pesquisadas:\n" + json.dumps(manifest, ensure_ascii=False, indent=2))

    for text_path in sorted(EXTRACTED_DIR.glob("*.txt")):
        text = text_path.read_text(encoding="utf-8", errors="ignore")
        if text.strip():
            chunks.append(f"\n--- {text_path.stem} ---\n{compact_text(text)}")

    context = "\n\n".join(chunks)
    return context[:max_chars]


def has_extracted_pdf_text() -> bool:
    extract_all_pdfs()
    return any(path.read_text(encoding="utf-8", errors="ignore").strip() for path in EXTRACTED_DIR.glob("*.txt"))


def source_status() -> dict[str, object]:
    extract_all_pdfs()
    pdfs = sorted(SOURCES_DIR.glob("*.pdf"))
    extracted = sorted(EXTRACTED_DIR.glob("*.txt"))
    return {
        "pdf_count": len(pdfs),
        "extracted_text_count": len(extracted),
        "manifest_exists": MANIFEST_PATH.exists(),
        "pdfs": [path.name for path in pdfs],
    }


def extract_all_pdfs() -> None:
    for pdf_path in sorted(SOURCES_DIR.glob("*.pdf")):
        target = EXTRACTED_DIR / f"{pdf_path.stem}.txt"
        if target.exists() and target.stat().st_mtime >= pdf_path.stat().st_mtime:
            continue
        reader = PdfReader(str(pdf_path))
        pages = []
        for page in reader.pages:
            pages.append(page.extract_text() or "")
        target.write_text("\n".join(pages), encoding="utf-8")


def compact_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    return text.strip()
