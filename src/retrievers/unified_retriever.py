"""Unified retrieval system with keyword-first search and venue prioritization."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from src.retrievers.semantic_scholar import SemanticScholarRetriever
from src.retrievers.arxiv_retriever import ArxivRetriever
from src.utils.storage import PaperStorage, PaperMetadata
from src.indexer.indexer import PaperIndexer
from src.utils.pdf_downloader import PDFDownloader
from src.config import MAX_PAPERS

DEFAULT_SOURCES = ["local", "semantic_scholar", "arxiv"]


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

        print(f"\n🔍 Keywords: {', '.join(keywords) if keywords else query_text}")

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
            except Exception as exc:
                print(f"   Error searching local storage: {exc}")

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
            except RuntimeError as exc:
                print(f"   ⚠️ Semantic Scholar error: {exc}")
            except Exception as exc:
                print(f"   ⚠️ Semantic Scholar error: {exc}")

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
            except Exception as exc:
                print(f"   ⚠️ arXiv error: {exc}")

        return self._finalize_results(all_papers)[:max_results]

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
                    print(f"   📥 Downloading PDF for arXiv:{arxiv_id}...")
                    pdf_content = self.pdf_downloader.download_arxiv(arxiv_id)
                elif pdf_url:
                    print(f"   📥 Downloading PDF from {pdf_url[:50]}...")
                    pdf_content = self.pdf_downloader.download(pdf_url)

            # Add to storage
            paper = self.storage.add_paper(
                enriched_data,
                pdf_content=pdf_content,
                is_internal=False,  # External papers go to papers_external/
            )

            return self._metadata_to_dict(paper)

        except Exception as e:
            print(f"   ⚠ Error adding paper: {e}")
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
        Retrieve papers related to a given paper's abstract/title.

        Args:
            paper_abstract: Abstract of the paper
            paper_title: Optional title of the paper
            max_results: Maximum number of results
            keywords: Optional manual keyword list
            download_pdfs: Whether to download PDFs
        """
        derived_keywords = self._sanitize_keywords(keywords) or self._derive_keywords(paper_abstract, paper_title)
        query_text = self._keywords_to_query(derived_keywords, paper_title or paper_abstract)
        return self.search_all_sources(
            keywords=derived_keywords,
            query=query_text,
            max_results=max_results,
            download_pdfs=download_pdfs,
        )

    @staticmethod
    def _keywords_to_query(keywords: List[str], fallback: Optional[str]) -> str:
        if keywords:
            return " ".join(keywords)
        return (fallback or "").strip()

    def _finalize_results(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        deduplicated = self._deduplicate_papers(papers)
        if not deduplicated:
            print("\n⚠️ No papers found for the provided keywords.")
        return self._sort_papers(deduplicated)

    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        return self.storage.get_statistics()
