"""arXiv API integration for keyword-first paper retrieval."""

from __future__ import annotations

import arxiv
from typing import Any, Dict, Iterable, List, Optional

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.llm import map_conference_to_abbreviation
from src.config import MAX_PAPERS


class ArxivRetriever:
    """Retrieve and normalize papers from arXiv."""

    def __init__(self):
        self.client = arxiv.Client()

    def search_papers(
        self,
        keywords: Optional[Iterable[str]] = None,
        max_results: int = MAX_PAPERS,
        query: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search arXiv using keyword-driven queries."""
        built_query = self._build_query(keywords, query)
        if not built_query:
            return []

        try:
            search = arxiv.Search(
                query=built_query,
                max_results=max_results,
                sort_by=arxiv.SortCriterion.Relevance,
            )
            return [self._normalize_paper(result) for result in self.client.results(search)]
        except Exception as exc:
            print(f"Error searching arXiv: {exc}")
            return []

    def _build_query(
        self,
        keywords: Optional[Iterable[str]],
        query: Optional[str],
    ) -> str:
        parts: List[str] = []
        if keywords:
            cleaned = [word.strip() for word in keywords if word and word.strip()]
            if cleaned:
                parts.append(" AND ".join(f'"{word}"' for word in cleaned))
        if query and query.strip():
            parts.append(query.strip())
        return " AND ".join(parts)

    def _normalize_paper(self, result: arxiv.Result) -> Dict[str, Any]:
        authors = [author.name for author in result.authors]
        arxiv_id = result.entry_id.rsplit("/", 1)[-1]
        year = result.published.year if result.published else None
        venue = result.journal_ref or ""
        conference_guess = self._guess_conference(venue or (result.comment or ""))
        conference = self._apply_conference_mapping(conference_guess or venue, fallback=conference_guess)

        return {
            "id": f"arXiv_{arxiv_id}",
            "title": result.title.strip(),
            "authors": authors,
            "abstract": result.summary.strip(),
            "year": year,
            "venue": venue,
            "conference": conference,
            "journal": venue,
            "url": result.entry_id,
            "pdf_url": result.pdf_url,
            "citations": 0,
            "source": "arxiv",
            "arxiv_id": arxiv_id,
        }

    @staticmethod
    def _guess_conference(text: str) -> str:
        if not text:
            return ""
        markers = [
            "CCS",
            "S&P",
            "USENIX Security",
            "NDSS",
            "ICSE",
            "FSE",
            "ISSTA",
            "ASE",
            "PLDI",
            "POPL",
            "OOPSLA",
            "SOSP",
            "OSDI",
            "NeurIPS",
            "ICML",
            "ICLR",
        ]
        lower = text.lower()
        for marker in markers:
            if marker.lower() in lower:
                return marker
        return text[:50].strip()

    @staticmethod
    def _apply_conference_mapping(label: str, fallback: Optional[str] = None) -> str:
        target = label or fallback or ""
        if not target:
            return ""
        try:
            mapped = map_conference_to_abbreviation(target)
            if mapped:
                return mapped
        except Exception:
            pass
        return fallback or target


if __name__ == "__main__":
    import json

    retriever = ArxivRetriever()

    print("Running manual retrieval checks against arXiv...\n")

    required_keys = {"id", "title", "authors", "year", "venue", "conference"}
    example_queries = [
        ("Blockchain fuzzing", ["blockchain", "fuzzing"], 3),
        ("Smart-contract security", ["smart contract", "security"], 3),
        ("Formal verification", ["formal verification", "ethereum"], 2),
        ("AI for smart contracts", ["machine learning", "smart contracts"], 2),
    ]

    def _sanity_check(papers: List[Dict[str, Any]]) -> bool:
        passed = True
        for idx, paper in enumerate(papers, start=1):
            missing = required_keys - paper.keys()
            if missing:
                passed = False
                print(f"   ⚠️ Paper {idx} missing keys: {sorted(missing)}")
        return passed

    for label, keywords, limit in example_queries:
        print(f"🔎 Example: {label}")
        print(f"   Keywords: {', '.join(keywords)}   (limit={limit})")

        papers = retriever.search_papers(keywords=keywords, max_results=limit)
        print(f"   Retrieved {len(papers)} paper(s)")

        tests_passed = _sanity_check(papers)
        print(f"   Basic key coverage test: {'PASSED' if tests_passed else 'FAILED'}")

        if papers:
            print("   Full records:")
            for paper in papers:
                print(json.dumps(paper, indent=2, ensure_ascii=False))
        print("-" * 80)
