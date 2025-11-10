"""Unified retrieval system with new storage backend."""

from typing import List, Dict, Any, Optional
from collections import defaultdict

from src.retrievers.semantic_scholar import SemanticScholarRetriever
from src.retrievers.arxiv_retriever import ArxivRetriever
from src.utils.storage import PaperStorage, PaperMetadata
from src.indexer.indexer import PaperIndexer
from src.utils.pdf_downloader import PDFDownloader
from src.config import MAX_PAPERS


class UnifiedRetrieverV2:
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
        if download_pdfs:
            self.pdf_downloader = PDFDownloader()

    def search_all_sources(
        self,
        query: str,
        max_results: int = MAX_PAPERS,
        sources: Optional[List[str]] = None,
        download_pdfs: bool = None,
    ) -> List[Dict[str, Any]]:
        """
        Search all sources and combine results.

        Priority:
        1. Check papers_internal/ first (manual papers)
        2. Check papers_external/ second (cached papers)
        3. Fetch from Semantic Scholar (better metadata quality)
        4. Fill remaining gap with arXiv (no limit, fetch as many as needed)
        5. Download PDFs and save to papers_external/

        Args:
            query: Search query string
            max_results: Maximum total results to return
            sources: List of sources to search (default: all)
            download_pdfs: Whether to download PDFs (default: use init setting)

        Returns:
            Combined list of papers from all sources
        """
        if sources is None:
            # NEW ORDER: Semantic Scholar before arXiv (better metadata)
            sources = ["local", "semantic_scholar", "arxiv"]

        if download_pdfs is None:
            download_pdfs = self.download_pdfs

        all_papers = []

        print(f"\n🔍 Searching for papers related to: '{query}'")
        print(f"Target: {max_results} papers from {len(sources)} source(s)\n")

        # 1. Search local storage first (internal + external)
        if "local" in sources:
            print("📚 Searching local storage (papers_internal + papers_external)...")
            try:
                local_papers = self.storage.search_papers(query=query, limit=max_results)
                print(f"   Found {len(local_papers)} papers locally")

                # Convert to dict format
                for paper in local_papers:
                    all_papers.append(self._metadata_to_dict(paper))

                # If we found enough papers locally, we can return
                if len(local_papers) >= max_results:
                    print(f"   ✓ Sufficient papers found locally!")
                    return all_papers[:max_results]

            except Exception as e:
                print(f"   Error searching local storage: {e}")

        # 2. Search Semantic Scholar FIRST (better metadata quality)
        if "semantic_scholar" in sources:
            needed = max_results - len(all_papers)
            if needed > 0:
                print(f"\n🎓 Searching Semantic Scholar first (need {needed} more papers, better metadata)...")
                try:
                    # Request exactly what we need
                    ss_papers = self.semantic_scholar.search_papers(query, needed)
                    print(f"   Found {len(ss_papers)} papers on Semantic Scholar")

                    new_papers = []
                    for paper in ss_papers:
                        normalized = self.semantic_scholar.normalize_paper(paper)
                        paper_id = normalized.get("id")

                        if not self.storage.paper_exists(paper_id):
                            new_papers.append(normalized)

                    print(f"   {len(new_papers)} new papers (not in local storage)")

                    # Add and index new papers
                    for paper in new_papers:
                        indexed_paper = self._add_and_index_paper(paper, download_pdfs)
                        if indexed_paper:
                            all_papers.append(indexed_paper)

                except Exception as e:
                    error_msg = str(e)
                    if "403" in error_msg or "Forbidden" in error_msg:
                        print(f"   ⚠️  Semantic Scholar: 403 Forbidden (authentication issue)")
                        print(f"   💡 Tip: Add SEMANTIC_SCHOLAR_API_KEY to .env for access")
                        print(f"   ✓  Continuing with arXiv and local papers...")
                    else:
                        print(f"   ⚠️  Semantic Scholar error: {e}")
                        print(f"   ✓  Continuing with arXiv and local papers...")

        # 3. Fill remaining gap with arXiv (no limit!)
        if "arxiv" in sources:
            needed = max_results - len(all_papers)
            if needed > 0:
                print(f"\n📄 Filling remaining gap with arXiv (need {needed} more papers)...")
                try:
                    # Fetch 2x what we need to account for potential duplicates
                    # (increased from 1.5x based on observed ~44% duplicate rate)
                    fetch_count = int(needed * 2)
                    arxiv_papers = self.arxiv.search_papers(query, fetch_count)
                    print(f"   Found {len(arxiv_papers)} papers on arXiv")

                    # Filter out papers we already have
                    new_papers = []
                    duplicate_count = 0
                    for paper in arxiv_papers:
                        paper_id = paper.get("id")
                        if not self.storage.paper_exists(paper_id):
                            new_papers.append(paper)
                        else:
                            duplicate_count += 1

                    print(f"   {len(new_papers)} new papers ({duplicate_count} duplicates filtered)")

                    # Add and index new papers
                    for paper in new_papers:
                        indexed_paper = self._add_and_index_paper(paper, download_pdfs)
                        if indexed_paper:
                            all_papers.append(indexed_paper)

                        # Stop if we have enough papers
                        if len(all_papers) >= max_results:
                            break

                    # If still short and we got many duplicates, warn user
                    still_needed = max_results - len(all_papers)
                    if still_needed > 0 and duplicate_count > len(new_papers):
                        print(f"   ℹ️  Still need {still_needed} more papers, but arXiv query exhausted")
                        print(f"   💡 Try different search terms or enable Semantic Scholar")

                except Exception as e:
                    print(f"   ⚠️  arXiv error: {e}")
                    print(f"   ✓  Continuing with {len(all_papers)} papers...")

        # Deduplicate by title
        deduplicated = self._deduplicate_papers(all_papers)
        print(f"\n✨ Total unique papers found: {len(deduplicated)}")

        if len(deduplicated) == 0:
            print("\n⚠️  No papers found. Try:")
            print("   • Using different search terms")
            print("   • Checking your internet connection (for arXiv/Semantic Scholar)")
            print("   • Adding SEMANTIC_SCHOLAR_API_KEY to .env for more sources")
            print("   • Running with --sources local to search only cached papers")

        # Sort by relevance
        sorted_papers = self._sort_papers(deduplicated)

        return sorted_papers[:max_results]

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
            "url": paper.url,
            "pdf_url": paper.pdf_url,
            "pdf_path": paper.pdf_path,
            "citations": paper.citations,
            "keywords": paper.keywords,
            "topics": paper.topics,
            "source": paper.source,
            "bibtex": paper.to_bibtex(),
        }

    def _deduplicate_papers(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate papers based on title similarity."""
        seen_titles = set()
        unique_papers = []

        for paper in papers:
            title = paper.get("title", "").lower().strip()
            if title and title not in seen_titles:
                seen_titles.add(title)
                unique_papers.append(paper)

        return unique_papers

    def _sort_papers(self, papers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sort papers by relevance (citation count and year)."""
        def sort_key(paper):
            citations = paper.get("citations", 0)
            year = paper.get("year", 0) or 0
            return (citations, year)

        return sorted(papers, key=sort_key, reverse=True)

    def retrieve_related_papers(
        self,
        paper_abstract: str,
        paper_title: Optional[str] = None,
        max_results: int = MAX_PAPERS,
        download_pdfs: bool = None,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve papers related to a given paper's abstract/title.

        Args:
            paper_abstract: Abstract of the paper
            paper_title: Optional title of the paper
            max_results: Maximum number of results
            download_pdfs: Whether to download PDFs

        Returns:
            List of related papers
        """
        query = self._extract_search_query(paper_abstract, paper_title)
        return self.search_all_sources(query, max_results, download_pdfs=download_pdfs)

    def _extract_search_query(self, abstract: str, title: Optional[str] = None) -> str:
        """Extract a search query from abstract and title."""
        # For better local search, extract key terms instead of using full text
        import re

        key_terms = []

        if title:
            # Extract important words from title (capitalized multi-word terms)
            # Skip common words
            stop_words = {'the', 'a', 'an', 'in', 'on', 'for', 'with', 'using', 'based'}
            words = title.lower().split()
            important_words = [w for w in words if len(w) > 3 and w not in stop_words]
            key_terms.extend(important_words[:5])  # Take first 5 important words

        if abstract and len(key_terms) < 3:
            # Extract first sentence and get key terms
            first_sentence = abstract.split('.')[0] if '.' in abstract else abstract[:100]
            words = first_sentence.lower().split()
            stop_words = {'the', 'a', 'an', 'in', 'on', 'for', 'with', 'this', 'that', 'these', 'those', 'are', 'is', 'be', 'been', 'being'}
            important_words = [w for w in words if len(w) > 4 and w not in stop_words]
            key_terms.extend(important_words[:3])

        # Join with spaces - will match papers that have ANY of these terms
        query = " ".join(key_terms[:5])  # Limit to 5 terms max
        return query if query else (title or abstract[:50])

    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        return self.storage.get_statistics()
