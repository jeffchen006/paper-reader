"""Unified retrieval system with keyword-first search and venue prioritization."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.retrievers.semantic_scholar import SemanticScholarRetriever
from src.retrievers.arxiv_retriever import ArxivRetriever
from src.utils.storage import PaperStorage, PaperMetadata
from src.indexer.indexer import PaperIndexer
from src.utils.pdf_downloader import PDFDownloader
from src.config import MAX_PAPERS

DEFAULT_SOURCES = ["local", "semantic_scholar", "arxiv"]
TOP_VENUES = {
    "s&p",
    "ccs",
    "usenix security",
    "ndss",
    "icse",
    "fse",
    "issta",
    "ase",
    "pldi",
    "popl",
    "oopsla",
    "sosp",
    "osdi",
    "neurips",
    "icml",
    "iclr",
}


class UnifiedRetriever:
    """Unified retriever with file-based storage and PDF download."""

    def __init__(
        self,
        internal_dir: str = "papers_internal",
        external_dir: str = "papers_external",
        download_pdfs: bool = True,
    ):
        """Initialize unified retriever with new storage."""
        self.storage = PaperStorage(internal_dir, external_dir)
        self.indexer = PaperIndexer()
        self.arxiv = ArxivRetriever()
        self.semantic_scholar = SemanticScholarRetriever()
        self.download_pdfs = download_pdfs
        self.pdf_downloader: Optional[PDFDownloader] = PDFDownloader() if download_pdfs else None

    def search_all_sources(
        self,
        keywords: Optional[Iterable[str]] = None,
        query: Optional[str] = None,
        max_results: int = MAX_PAPERS,
        sources: Optional[List[str]] = None,
        download_pdfs: bool = None,
    ) -> List[Dict[str, Any]]:
        """
        Search local storage plus remote APIs using keyword-driven queries.
        """
        keywords = self._sanitize_keywords(keywords)
        query_text = self._keywords_to_query(keywords, query)
        if not query_text:
            raise ValueError("Provide keywords or a query string.")

        sources = sources or DEFAULT_SOURCES
        download_pdfs = self.download_pdfs if download_pdfs is None else download_pdfs

        all_papers: List[Dict[str, Any]] = []
        seen_ids: set[str] = set()

        def append(paper_dict: Dict[str, Any]) -> None:
            paper_id = paper_dict.get("id")
            if paper_id and paper_id not in seen_ids:
                seen_ids.add(paper_id)
                all_papers.append(paper_dict)

        if "local" in sources:
            try:
                local_matches = self.storage.search_papers(
                    query=query_text,
                    keywords=keywords or None,
                    limit=max_results,
                )
                for paper in local_matches:
                    append(self._metadata_to_dict(paper))
                if len(all_papers) >= max_results:
                    return self._finalize_results(all_papers)[:max_results]
            except Exception:
                pass

        if "semantic_scholar" in sources and len(all_papers) < max_results:
            needed = max_results - len(all_papers)
            try:
                ss_papers = self.semantic_scholar.search_papers(
                    keywords=keywords or None,
                    query=query_text,
                    max_results=needed,
                )
                for paper in ss_papers:
                    if self.storage.paper_exists(paper["id"]):
                        continue
                    indexed = self._add_and_index_paper(paper, download_pdfs)
                    if indexed:
                        append(indexed)
                    if len(all_papers) >= max_results:
                        break
            except Exception:
                pass

        if "arxiv" in sources and len(all_papers) < max_results:
            needed = max_results - len(all_papers)
            fetch_count = max(needed * 2, needed)
            try:
                arxiv_papers = self.arxiv.search_papers(
                    keywords=keywords or None,
                    query=query_text,
                    max_results=fetch_count,
                )
                for paper in arxiv_papers:
                    if self.storage.paper_exists(paper["id"]):
                        continue
                    indexed = self._add_and_index_paper(paper, download_pdfs)
                    if indexed:
                        append(indexed)
                    if len(all_papers) >= max_results:
                        break
            except Exception:
                pass

        return self._finalize_results(all_papers, keywords, query_text)[:max_results]

    def _add_and_index_paper(
        self,
        paper_data: Dict[str, Any],
        download_pdf: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """
        Add paper to external storage with indexing and optional PDF download.

        Args:
            paper_data: Paper metadata
            download_pdf: Whether to download PDF

        Returns:
            Indexed paper dict or None
        """
        try:
            # Enrich with keywords and topics
            enriched_data = self.indexer.normalize_paper_data(paper_data)

            # Download PDF if enabled
            pdf_content = None
            if download_pdf:
                if self.pdf_downloader is None:
                    self.pdf_downloader = PDFDownloader()
                pdf_url = enriched_data.get("pdf_url")
                arxiv_id = enriched_data.get("arxiv_id")

                if arxiv_id:
                    pdf_content = self.pdf_downloader.download_arxiv(arxiv_id)
                elif pdf_url:
                    pdf_content = self.pdf_downloader.download(pdf_url)

            # Add to storage
            paper = self.storage.add_paper(
                enriched_data,
                pdf_content=pdf_content,
                is_internal=False,  # External papers go to papers_external/
            )

            return self._metadata_to_dict(paper)

        except Exception:
            return None

    def _metadata_to_dict(self, paper: PaperMetadata) -> Dict[str, Any]:
        """Convert PaperMetadata to dict."""
        return {
            "id": paper.paper_id,
            "title": paper.title,
            "authors": paper.authors,
            "year": paper.year,
            "abstract": paper.abstract,
            "venue": paper.venue,
            "conference": paper.conference,
            "journal": paper.journal,
            "url": paper.url,
            "pdf_url": paper.pdf_url,
            "pdf_path": paper.pdf_path,
            "citations": paper.citations,
            "keywords": paper.keywords,
            "topics": paper.topics,
            "source": paper.source,
            "bibtex": paper.to_bibtex(),
        }
    def retrieve_related_papers(
        self,
        paper_abstract: str,
        paper_title: Optional[str] = None,
        keywords: Optional[Iterable[str]] = None,
        max_results: int = MAX_PAPERS,
        download_pdfs: bool = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve the exact paper matching the provided title.
        """
        if not paper_title:
            raise ValueError("Paper title is required for exact retrieval.")

        normalized_title = paper_title.strip().lower()
        derived_keywords = self._sanitize_keywords(keywords) or self._derive_keywords("", paper_title)
        query_text = paper_title

        candidates = self.search_all_sources(
            keywords=derived_keywords,
            query=query_text,
            max_results=max_results,
            download_pdfs=download_pdfs,
        )

        matches = [
            paper for paper in candidates
            if (paper.get("title") or "").strip().lower() == normalized_title
        ]

        return matches[:1]

    @staticmethod
    def _keywords_to_query(keywords: List[str], fallback: Optional[str]) -> str:
        if keywords:
            return " ".join(keywords)
        return (fallback or "").strip()

    def _finalize_results(
        self,
        papers: List[Dict[str, Any]],
        keywords: List[str],
        query_text: str,
    ) -> List[Dict[str, Any]]:
        deduplicated = self._deduplicate_papers(papers)
        if not deduplicated:
            print(f"\n⚠️ No papers found for keywords: {', '.join(keywords) if keywords else query_text}")
        return self._sort_papers(deduplicated)

    def _deduplicate_papers(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen = set()
        unique: List[Dict[str, Any]] = []
        for paper in papers:
            title = (paper.get("title") or "").strip().lower()
            if title and title not in seen:
                seen.add(title)
                unique.append(paper)
        return unique

    def _sort_papers(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        def sort_key(paper: Dict[str, Any]):
            venue_boost = 1 if self._is_top_venue(paper) else 0
            citations = paper.get("citations") or 0
            year = paper.get("year") or 0
            return (venue_boost, citations, year)

        return sorted(papers, key=sort_key, reverse=True)

    @staticmethod
    def _is_top_venue(paper: Dict[str, Any]) -> bool:
        venue_text = (
            (paper.get("conference") or "")
            or (paper.get("venue") or "")
            or (paper.get("journal") or "")
        ).lower()
        for keyword in TOP_VENUES:
            if keyword in venue_text:
                return True
        return False

    @staticmethod
    def _sanitize_keywords(keywords: Optional[Iterable[str]]) -> List[str]:
        sanitized: List[str] = []
        if not keywords:
            return sanitized
        for keyword in keywords:
            if not keyword:
                continue
            clean = keyword.strip()
            if clean and clean not in sanitized:
                sanitized.append(clean)
        return sanitized

    @staticmethod
    def _derive_keywords(abstract: str, title: Optional[str]) -> List[str]:
        stop_words = {
            "the",
            "a",
            "an",
            "in",
            "on",
            "for",
            "with",
            "using",
            "based",
            "this",
            "that",
            "these",
            "those",
            "are",
            "is",
            "be",
            "been",
            "being",
        }
        keywords: List[str] = []

        def add_terms(text: str, limit: int) -> None:
            for word in re.findall(r"[a-zA-Z][a-zA-Z0-9-]+", text.lower()):
                if len(word) > 3 and word not in stop_words and word not in keywords:
                    keywords.append(word)
                if len(keywords) >= limit:
                    break

        if title:
            add_terms(title, 5)

        if abstract and len(keywords) < 5:
            first_sentence = abstract.split(".")[0] if "." in abstract else abstract
            add_terms(first_sentence, 5)

        return keywords

    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        return self.storage.get_statistics()


if __name__ == "__main__":
    retriever = UnifiedRetriever(download_pdfs=False)
    # keyword_examples = [
    #     ("Blockchain fuzzing", ["blockchain", "fuzzing"], 3),
    #     ("Smart-contract security", ["smart contract", "security"], 3),
    # ]

    # for label, keywords, limit in keyword_examples:
    #     print(f"\n🔎 {label} (limit={limit})")
    #     try:
    #         papers = retriever.search_all_sources(
    #             keywords=keywords,
    #             max_results=limit,
    #             sources=["local"],
    #             download_pdfs=False,
    #         )
    #         for paper in papers:
    #             print(paper, json.dumps(paper, indent=2))
    #     except Exception as exc:
    #         print(f"   ❌ Retrieval error: {exc}")

    print("\n🔍 Keyword example (local + arXiv)")
    try:
        papers = retriever.search_all_sources(
            keywords=["smart contract", "fuzzer"],
            max_results=1,
            sources=["local", "arxiv"],
            download_pdfs=False,
        )
        print(f"   Retrieved {len(papers)} paper(s)")
    except Exception as exc:
        print(f"   ❌ Retrieval error: {exc}")

    print("\n📝 Title-only retrieval example")
    try:
        papers = retriever.retrieve_related_papers(
            paper_abstract="",
            paper_title="ityfuzz: Snapshot-Based Fuzzer for Smart Contract",
            max_results=1,
            download_pdfs=False,
        )
        for paper in papers:
            print(paper, json.dumps(paper, indent=2))
    except Exception as exc:
        print(f"   ❌ Retrieval error: {exc}")


    print("\n✅ Exact-match smoke test (ityfuzz)")
    try:
        exact = retriever.retrieve_related_papers(
            paper_abstract="",
            paper_title="ityfuzz: Snapshot-Based Fuzzer for Smart Contract",
            max_results=1,
            download_pdfs=False,
        )
        print(exact)
    except Exception as exc:
        print(f"   ❌ Exact-match test error: {exc}")
