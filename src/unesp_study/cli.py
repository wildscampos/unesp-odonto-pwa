from __future__ import annotations

import argparse
from datetime import date, datetime

from .generator import generate_answers_pdf, generate_exam_pdf
from .schedule import run_scheduled_day
from .sources import source_status
from .web_export import export_web_data


def parse_date(value: str | None) -> date:
    if not value:
        return date.today()
    return datetime.strptime(value, "%Y-%m-%d").date()


def main() -> None:
    parser = argparse.ArgumentParser(description="Gerador de provas Unesp em PDF.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    exam_parser = subparsers.add_parser("exam", help="gera uma prova")
    exam_parser.add_argument("--date", help="data no formato AAAA-MM-DD")

    answers_parser = subparsers.add_parser("answers", help="gera resolucao de uma prova")
    answers_parser.add_argument("--date", help="data no formato AAAA-MM-DD")

    run_parser = subparsers.add_parser("run", help="executa a acao programada do dia")
    run_parser.add_argument("--date", help="data base no formato AAAA-MM-DD")

    subparsers.add_parser("sources", help="mostra PDFs reais carregados em sources/")
    subparsers.add_parser("export-web", help="exporta provas salvas para o PWA")

    args = parser.parse_args()
    selected_date = parse_date(getattr(args, "date", None))

    if args.command == "exam":
        print(generate_exam_pdf(selected_date))
    elif args.command == "answers":
        print(generate_answers_pdf(selected_date))
    elif args.command == "run":
        for result in run_scheduled_day(selected_date):
            print(result)
    elif args.command == "sources":
        status = source_status()
        print(f"PDFs em sources/: {status['pdf_count']}")
        print(f"Textos extraidos: {status['extracted_text_count']}")
        print(f"Manifesto de fontes: {'sim' if status['manifest_exists'] else 'nao'}")
        for pdf_name in status["pdfs"]:
            print(f"- {pdf_name}")
    elif args.command == "export-web":
        print(export_web_data())
