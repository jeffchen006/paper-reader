"""Semantic Scholar API integration for paper retrieval."""

from __future__ import annotations

import sys
from pathlib import Path
import time
import requests
from typing import Any, Dict, Iterable, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.llm import map_conference_to_abbreviation
from src.config import (
    SEMANTIC_SCHOLAR_BASE_URL,
    SEMANTIC_SCHOLAR_API_KEY,
    SEMANTIC_SCHOLAR_RATE_LIMIT,
    MAX_PAPERS,
)


class SemanticScholarRetriever:
    """Retrieve and normalize Semantic Scholar results."""

    DEFAULT_FIELDS = [
        "paperId",
        "title",
        "abstract",
        "authors",
        "year",
        "venue",
        "journal",
        "citationCount",
        "url",
        "openAccessPdf",
    ]

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or SEMANTIC_SCHOLAR_API_KEY
        self.base_url = SEMANTIC_SCHOLAR_BASE_URL
        self.rate_limit = SEMANTIC_SCHOLAR_RATE_LIMIT
        self.headers = {"X-API-KEY": self.api_key} if self.api_key else {}
        if not self.api_key:
            print("   ℹ️ Semantic Scholar API key missing, using public tier.")

    def search_papers(
        self,
        keywords: Optional[Iterable[str]] = None,
        max_results: int = MAX_PAPERS,
        fields: Optional[List[str]] = None,
        query: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search Semantic Scholar using keyword-first queries."""
        built_query = self._build_query(keywords, query)
        if not built_query:
            return []

        fields = fields or self.DEFAULT_FIELDS
        papers: List[Dict[str, Any]] = []
        offset = 0
        limit = min(100, max_results)

        while len(papers) < max_results:
            try:
                time.sleep(self.rate_limit)
                params = {
                    "query": built_query,
                    "limit": limit,
                    "offset": offset,
                    "fields": ",".join(fields),
                }
                response = requests.get(
                    f"{self.base_url}/paper/search",
                    params=params,
                    headers=self.headers,
                    timeout=30,
                )
                if response.status_code == 200:
                    data = response.json()
                    batch = data.get("data", [])
                    if not batch:
                        break
                    papers.extend(self._normalize_paper(p) for p in batch)
                    offset += limit
                    total = data.get("total", 0)
                    if offset >= total:
                        break
                elif response.status_code == 429:
                    time.sleep(5)
                    continue
                elif response.status_code == 403:
                    message = "403 Forbidden - set SEMANTIC_SCHOLAR_API_KEY in .env."
                    raise RuntimeError(message)
                else:
                    raise RuntimeError(f"{response.status_code}: {response.text}")
            except Exception:
                raise

        return papers[:max_results]

    def get_recommendations(
        self,
        paper_id: str,
        max_results: int = MAX_PAPERS,
    ) -> List[Dict[str, Any]]:
        """Return normalized recommendations for a given paper."""
        try:
            time.sleep(self.rate_limit)
            params = {
                "fields": ",".join(self.DEFAULT_FIELDS),
                "limit": max_results,
            }
            response = requests.get(
                f"{self.base_url}/paper/{paper_id}/recommendations",
                params=params,
                headers=self.headers,
                timeout=30,
            )
            if response.status_code == 200:
                data = response.json().get("recommendedPapers", [])
                return [self._normalize_paper(paper) for paper in data]
            print(f"Error: {response.status_code} - {response.text}")
        except Exception as exc:
            print(f"Error fetching recommendations: {exc}")
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
                parts.append(" ".join(cleaned))
        if query and query.strip():
            parts.append(query.strip())
        return " ".join(parts)

    @staticmethod
    def _normalize_paper(paper: Dict[str, Any]) -> Dict[str, Any]:
        authors = [author.get("name") for author in paper.get("authors", []) if author.get("name")]
        venue = paper.get("venue") or paper.get("journal") or ""
        conference_guess = SemanticScholarRetriever._guess_conference(venue)
        conference = SemanticScholarRetriever._apply_conference_mapping(conference_guess or venue, fallback=conference_guess)
        pdf_source = paper.get("openAccessPdf") or {}

        return {
            "id": f"SS_{paper.get('paperId')}",
            "title": (paper.get("title") or "").strip(),
            "authors": authors,
            "abstract": (paper.get("abstract") or "").strip(),
            "year": paper.get("year"),
            "venue": venue,
            "conference": conference,
            "journal": paper.get("journal"),
            "url": paper.get("url"),
            "pdf_url": pdf_source.get("url"),
            "citations": paper.get("citationCount", 0) or 0,
            "source": "semantic_scholar",
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

    retriever = SemanticScholarRetriever()

    print("Running manual retrieval checks against Semantic Scholar...\n")

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

        try:
            papers = retriever.search_papers(keywords=keywords, max_results=limit)
            print(f"   Retrieved {len(papers)} paper(s)")
            tests_passed = _sanity_check(papers)
            print(f"   Basic key coverage test: {'PASSED' if tests_passed else 'FAILED'}")

            if papers:
                print("   Full records:")
                for paper in papers:
                    print(json.dumps(paper, indent=2, ensure_ascii=False))
        except Exception as exc:
            print(f"   ❌ Retrieval error: {exc}")
        print("-" * 80)
