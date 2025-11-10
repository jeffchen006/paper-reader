"""arXiv API integration for paper retrieval."""

import arxiv
from typing import List, Dict, Any
from tqdm import tqdm

from src.config import MAX_PAPERS


class ArxivRetriever:
    """Retrieve papers from arXiv."""

    def __init__(self):
        """Initialize the arXiv retriever."""
        self.client = arxiv.Client()

    def search_papers(self, query: str, max_results: int = MAX_PAPERS) -> List[Dict[str, Any]]:
        """
        Search for papers on arXiv.

        Args:
            query: Search query string
            max_results: Maximum number of results to return

        Returns:
            List of paper dictionaries
        """
        papers = []

        try:
            search = arxiv.Search(
                query=query,
                max_results=max_results,  # No hardcoded limit - fetch as many as requested
                sort_by=arxiv.SortCriterion.Relevance
            )

            results = list(self.client.results(search))

            for result in tqdm(results, desc="Fetching from arXiv"):
                papers.append(self.normalize_paper(result))

        except Exception as e:
            print(f"Error searching arXiv: {e}")

        return papers

