#!/usr/bin/env python3
"""
Automatic cleaning script for papers_external/ directory.

For each PDF in pdfs/, checks if a corresponding metadata file exists in metadata/.
If not, creates metadata by parsing the PDF and using PaperIndexer.
After processing all PDFs, deletes metadata files that don't have corresponding PDFs.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
import sys

from pypdf import PdfReader

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.indexer.indexer import PaperIndexer

BASE_DIR = Path(__file__).resolve().parent
PDF_DIR = BASE_DIR / "pdfs"
METADATA_DIR = BASE_DIR / "metadata"


def extract_pdf_text(pdf_path: Path, max_pages: int = 5) -> str:
    """Extract text from the first few pages of a PDF."""
    try:
        reader = PdfReader(str(pdf_path))
        pages = reader.pages[:max_pages]
        text = "\n".join((page.extract_text() or "") for page in pages)
        return text.strip()
    except Exception as exc:
        print(f"⚠️  Failed to read {pdf_path.name}: {exc}")
        return ""


def infer_title(text: str, fallback: str) -> str:
    """Guess the paper title from the first non-empty line of text."""
    for line in text.splitlines():
        clean = line.strip()
        if len(clean) >= 10:
            return clean[:300]
    return fallback.replace("_", " ")


def infer_year(text: str) -> int | None:
    """Extract the first four-digit year found in the text."""
    match = re.search(r"(20\d{2}|19\d{2})", text)
    return int(match.group(0)) if match else None


def ensure_metadata_for_pdf(pdf_path: Path, indexer: PaperIndexer) -> None:
    """Create metadata for a PDF if it doesn't already exist."""
    metadata_path = METADATA_DIR / f"{pdf_path.stem}.json"
    if metadata_path.exists():
        return

    text = extract_pdf_text(pdf_path)
    title = infer_title(text, pdf_path.stem)
    abstract = text[:1500]
    year = infer_year(text)

    metadata = {
        "paper_id": f"auto_{pdf_path.stem}",
        "title": title,
        "authors": [],
        "year": year,
        "abstract": abstract,
        "venue": "",
        "conference": "",
        "journal": "",
        "volume": "",
        "pages": "",
        "doi": "",
        "arxiv_id": None,
        "url": "",
        "pdf_url": "",
        "pdf_path": str(pdf_path),
        "citations": 0,
        "keywords": [],
        "topics": [],
        "source": "autoclean",
    }

    enriched = indexer.normalize_paper_data(metadata)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    with metadata_path.open("w", encoding="utf-8") as f:
        json.dump(enriched, f, indent=2, ensure_ascii=False)
    print(f"✅ Created metadata for {pdf_path.name}")


def remove_orphan_metadata() -> None:
    """Delete metadata files that no longer have corresponding PDFs."""
    for meta_file in METADATA_DIR.glob("*.json"):
        pdf_file = PDF_DIR / (meta_file.stem + ".pdf")
        if not pdf_file.exists():
            meta_file.unlink()
            print(f"🗑️  Removed orphan metadata {meta_file.name}")


def main():
    PDF_DIR.mkdir(exist_ok=True)
    METADATA_DIR.mkdir(exist_ok=True)

    indexer = PaperIndexer()

    for pdf_path in sorted(PDF_DIR.glob("*.pdf")):
        ensure_metadata_for_pdf(pdf_path, indexer)

    remove_orphan_metadata()


if __name__ == "__main__":
    main()
