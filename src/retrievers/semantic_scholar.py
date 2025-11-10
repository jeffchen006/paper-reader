"""Semantic Scholar API integration for paper retrieval."""

import time
import requests
from typing import List, Dict, Any, Optional
from tqdm import tqdm

from src.config import (
    SEMANTIC_SCHOLAR_BASE_URL,
    SEMANTIC_SCHOLAR_API_KEY,
    SEMANTIC_SCHOLAR_RATE_LIMIT,
    MAX_PAPERS
)


class SemanticScholarRetriever:
    """Retrieve papers from Semantic Scholar API."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the Semantic Scholar retriever."""
        self.api_key = api_key or SEMANTIC_SCHOLAR_API_KEY
        self.base_url = SEMANTIC_SCHOLAR_BASE_URL
        self.rate_limit = SEMANTIC_SCHOLAR_RATE_LIMIT
        self.headers = {}
        if self.api_key:
            # Use uppercase header name to match official Semantic Scholar API examples
            # See: https://github.com/allenai/s2-folks/tree/main/examples/python
            self.headers["X-API-KEY"] = self.api_key
        else:
            print("   ℹ️  No Semantic Scholar API key found. Using public rate limits.")

    def search_papers(self, query: str, max_results: int = MAX_PAPERS,
                     fields: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Search for papers using Semantic Scholar API.

        Args:
            query: Search query string
            max_results: Maximum number of results to return
            fields: List of fields to return (default: all useful fields)

        Returns:
            List of paper dictionaries
        """
        if fields is None:
            fields = [
                "paperId", "title", "abstract", "authors", "year",
                "venue", "citationCount", "url", "openAccessPdf"
            ]

        papers = []
        offset = 0
        limit = min(100, max_results)  # API limit is 100 per request

        with tqdm(total=max_results, desc="Fetching from Semantic Scholar") as pbar:
            while len(papers) < max_results:
                try:
                    time.sleep(self.rate_limit)  # Rate limiting

                    params = {
                        "query": query,
                        "limit": limit,
                        "offset": offset,
                        "fields": ",".join(fields)
                    }

                    response = requests.get(
                        f"{self.base_url}/paper/search",
                        params=params,
                        headers=self.headers,
                        timeout=30
                    )

                    if response.status_code == 200:
                        data = response.json()
                        batch = data.get("data", [])

                        if not batch:
                            break

                        papers.extend(batch)
                        pbar.update(len(batch))
                        offset += limit

                        # Check if we've retrieved all available results
                        total = data.get("total", 0)
                        if offset >= total or len(papers) >= max_results:
                            break
                    elif response.status_code == 429:
                        # Rate limited, wait and retry
                        time.sleep(5)
                        continue
                    elif response.status_code == 403:
                        # Forbidden - likely authentication issue
                        if self.api_key:
                            raise Exception(f"403 Forbidden - API key may be invalid. Please check your SEMANTIC_SCHOLAR_API_KEY.")
                        else:
                            raise Exception(f"403 Forbidden - No API key provided. Add SEMANTIC_SCHOLAR_API_KEY to .env for access.")
                    else:
                        # Other errors
                        raise Exception(f"{response.status_code} - {response.text}")

                except Exception as e:
                    # Re-raise to let caller handle it properly
                    raise e

        return papers[:max_results]


    def get_recommendations(self, paper_id: str,
                          max_results: int = MAX_PAPERS) -> List[Dict[str, Any]]:
        """
        Get paper recommendations based on a seed paper.

        Args:
            paper_id: Semantic Scholar paper ID
            max_results: Maximum number of recommendations

        Returns:
            List of recommended papers
        """
        try:
            time.sleep(self.rate_limit)

            params = {
                "fields": "paperId,title,abstract,authors,year,venue,citationCount,url",
                "limit": max_results
            }

            response = requests.get(
                f"{self.base_url}/paper/{paper_id}/recommendations",
                params=params,
                headers=self.headers,
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("recommendedPapers", [])
            else:
                print(f"Error: {response.status_code} - {response.text}")
                return []

        except Exception as e:
            print(f"Error fetching recommendations: {e}")
            return []

