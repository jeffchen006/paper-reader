"""Paper storage system with PDF files and metadata indexes."""

import os
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import re


class PaperMetadata:
    """Metadata schema for a paper with BibTeX support."""

    def __init__(
        self,
        paper_id: str,
        title: str,
        authors: List[str],
        year: Optional[int] = None,
        abstract: Optional[str] = None,
        venue: Optional[str] = None,
        conference: Optional[str] = None,
        journal: Optional[str] = None,
        volume: Optional[str] = None,
        pages: Optional[str] = None,
        doi: Optional[str] = None,
        arxiv_id: Optional[str] = None,
        url: Optional[str] = None,
        pdf_url: Optional[str] = None,
        pdf_path: Optional[str] = None,
        citations: int = 0,
        keywords: List[str] = None,
        topics: List[str] = None,
        source: str = "unknown",
        added_date: Optional[str] = None,
    ):
        """Initialize paper metadata."""
        self.paper_id = paper_id
        self.title = title
        self.authors = authors or []
        self.year = year
        self.abstract = abstract or ""
        self.venue = venue
        self.conference = conference
        self.journal = journal
        self.volume = volume
        self.pages = pages
        self.doi = doi
        self.arxiv_id = arxiv_id
        self.url = url
        self.pdf_url = pdf_url
        self.pdf_path = pdf_path
        self.citations = citations
        self.keywords = keywords or []
        self.topics = topics or []
        self.source = source
        self.added_date = added_date or datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "paper_id": self.paper_id,
            "title": self.title,
            "authors": self.authors,
            "year": self.year,
            "abstract": self.abstract,
            "venue": self.venue,
            "conference": self.conference,
            "journal": self.journal,
            "volume": self.volume,
            "pages": self.pages,
            "doi": self.doi,
            "arxiv_id": self.arxiv_id,
            "url": self.url,
            "pdf_url": self.pdf_url,
            "pdf_path": self.pdf_path,
            "citations": self.citations,
            "keywords": self.keywords,
            "topics": self.topics,
            "source": self.source,
            "added_date": self.added_date,
            "bibtex": self.to_bibtex(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PaperMetadata":
        """Create from dictionary."""
        # Remove bibtex from data as it's generated
        data_copy = data.copy()
        data_copy.pop("bibtex", None)
        return cls(**data_copy)

    def to_bibtex(self) -> str:
        """
        Generate BibTeX citation in Google Scholar format.

        Supports: @article, @inproceedings, @misc (for arXiv)
        """
        # Generate citation key: FirstAuthorLastNameYear
        if self.authors:
            first_author = self.authors[0].strip()
            author_parts = first_author.split()
            last_name = author_parts[-1] if author_parts else "Unknown"
            # Remove special characters
            last_name = re.sub(r'[^a-zA-Z]', '', last_name)
        else:
            last_name = "Unknown"

        year_str = str(self.year) if self.year else "n.d."
        citation_key = f"{last_name}{year_str}"

        # Format authors for BibTeX
        author_str = " and ".join(self.authors) if self.authors else "Unknown"

        # Determine entry type
        if self.journal:
            entry_type = "article"
        elif self.conference or (self.venue and any(
            keyword in self.venue.lower()
            for keyword in ["conference", "symposium", "workshop", "proceedings"]
        )):
            entry_type = "inproceedings"
        elif self.arxiv_id:
            entry_type = "misc"
        else:
            entry_type = "article"

        # Build BibTeX entry
        bibtex_lines = [f"@{entry_type}{{{citation_key},"]

        # Required fields
        bibtex_lines.append(f'  title={{{self.title}}},')
        bibtex_lines.append(f'  author={{{author_str}}},')

        if self.year:
            bibtex_lines.append(f'  year={{{self.year}}},')

        # Optional fields based on entry type
        if entry_type == "article":
            if self.journal:
                bibtex_lines.append(f'  journal={{{self.journal}}},')
            elif self.venue:
                bibtex_lines.append(f'  journal={{{self.venue}}},')

            if self.volume:
                bibtex_lines.append(f'  volume={{{self.volume}}},')

            if self.pages:
                bibtex_lines.append(f'  pages={{{self.pages}}},')

        elif entry_type == "inproceedings":
            if self.conference:
                bibtex_lines.append(f'  booktitle={{{self.conference}}},')
            elif self.venue:
                bibtex_lines.append(f'  booktitle={{{self.venue}}},')

            if self.pages:
                bibtex_lines.append(f'  pages={{{self.pages}}},')

        elif entry_type == "misc":
            if self.arxiv_id:
                bibtex_lines.append(f'  note={{arXiv preprint arXiv:{self.arxiv_id}}},')

        # Common optional fields
        if self.doi:
            bibtex_lines.append(f'  doi={{{self.doi}}},')

        if self.url:
            bibtex_lines.append(f'  url={{{self.url}}},')

        # Remove trailing comma from last field
        if bibtex_lines[-1].endswith(','):
            bibtex_lines[-1] = bibtex_lines[-1][:-1]

        bibtex_lines.append("}")

        return "\n".join(bibtex_lines)


class PaperStorage:
    """Manages paper storage with internal and external collections."""

    def __init__(
        self,
        internal_dir: str = "papers_internal",
        external_dir: str = "papers_external",
    ):
        """Initialize paper storage."""
        self.internal_dir = Path(internal_dir)
        self.external_dir = Path(external_dir)

        # Create directories
        self.internal_dir.mkdir(exist_ok=True)
        self.external_dir.mkdir(exist_ok=True)

        # Create subdirectories for organization
        for base_dir in [self.internal_dir, self.external_dir]:
            (base_dir / "pdfs").mkdir(exist_ok=True)
            (base_dir / "metadata").mkdir(exist_ok=True)

        # Build indexes
        self._build_indexes()

    def _build_indexes(self):
        """Build indexes from metadata files."""
        self.internal_index = self._load_index(self.internal_dir)
        self.external_index = self._load_index(self.external_dir)

        # Combined index for searching
        self.all_papers = {**self.internal_index, **self.external_index}

    def _load_index(self, directory: Path) -> Dict[str, PaperMetadata]:
        """Load all metadata files from a directory."""
        index = {}
        metadata_dir = directory / "metadata"

        if not metadata_dir.exists():
            return index

        for metadata_file in metadata_dir.glob("*.json"):
            try:
                with open(metadata_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    paper = PaperMetadata.from_dict(data)
                    index[paper.paper_id] = paper
            except Exception as e:
                print(f"Warning: Could not load {metadata_file}: {e}")

        return index

    def _sanitize_filename(self, text: str, max_length: int = 100) -> str:
        """Sanitize text for use as filename."""
        # Remove special characters
        text = re.sub(r'[<>:"/\\|?*]', '', text)
        # Replace spaces and special chars with underscores
        text = re.sub(r'[\s\-:]+', '_', text)
        # Remove multiple underscores
        text = re.sub(r'_+', '_', text)
        # Truncate if too long
        if len(text) > max_length:
            text = text[:max_length]
        # Remove trailing underscore
        text = text.rstrip('_')
        return text

    def _extract_conference_abbrev(self, paper_data: Dict[str, Any]) -> str:
        """
        Extract conference abbreviation for naming.
        Prioritizes actual conference over venue.

        Args:
            paper_data: Paper metadata with 'conference', 'venue', 'year'

        Returns:
            Conference abbreviation with year (e.g., "CCS24", "ICSE23")
        """
        conference = paper_data.get("conference")
        venue = paper_data.get("venue")
        year = paper_data.get("year")

        year_str = str(year)[-2:] if year else "XX"  # Last 2 digits of year

        # If we have explicit conference field, use it
        if conference:
            conf_upper = conference.upper().strip()

            # Map to standard abbreviations for known top-tier conferences
            conf_map = {
                'CCS': 'CCS',
                'SP': 'SP',
                'S&P': 'SP',
                'SEC': 'SEC',
                'SECURITY': 'SEC',
                'NDSS': 'NDSS',
                'SOSP': 'SOSP',
                'OSDI': 'OSDI',
                'PLDI': 'PLDI',
                'POPL': 'POPL',
                'OOPSLA': 'OOPSLA',
                'ICSE': 'ICSE',
                'FSE': 'FSE',
                'ASE': 'ASE',
                'ISSTA': 'ISSTA',
                'SANER': 'SANER',
                'ICSME': 'ICSME',
            }

            for key, abbrev in conf_map.items():
                if key in conf_upper:
                    return f"{abbrev}{year_str}"

            # If conference is set but not in our map, use it as-is
            # (e.g., IWBOSE, workshop names, etc.)
            # Avoid using generic publishers
            if conference and conference not in ['IEEE', 'ACM', 'Springer']:
                # Skip arXiv categories (they start with "arXiv:")
                if conference.startswith('arXiv:'):
                    # Will fall through to venue processing
                    pass
                else:
                    # Clean up the conference name (remove dots, colons, spaces)
                    clean_conf = re.sub(r'[:\s.]+', '', conference)
                    return f"{clean_conf}{year_str}"

        # Fallback to venue
        if not venue:
            return f"{year}" if year else "Unknown"

        venue_upper = venue.upper()

        # Top-tier conferences (check in venue string)
        top_conferences = {
            'CCS': 'CCS',
            'IEEE S&P': 'SP',
            'USENIX SECURITY': 'SEC',
            'NDSS': 'NDSS',
            'SOSP': 'SOSP',
            'OSDI': 'OSDI',
            'PLDI': 'PLDI',
            'POPL': 'POPL',
            'OOPSLA': 'OOPSLA',
            'ICSE': 'ICSE',
            'FSE': 'FSE',
            'ASE': 'ASE',
            'ISSTA': 'ISSTA',
        }

        # Check for top conferences first
        for full_name, abbrev in top_conferences.items():
            if full_name in venue_upper:
                return f"{abbrev}{year_str}"

        # Check for arXiv (only if no real conference was found)
        if 'ARXIV' in venue_upper:
            # Extract category if available (e.g., cs.CR -> CSCR)
            match = re.search(r'ARXIV[:\s]*([A-Z]+)\.([A-Z]+)', venue_upper)
            if match:
                # Combine category parts without dot (cs.CR -> CSCR)
                category = match.group(1) + match.group(2)
                return f"arXiv{category}{year_str}"
            return f"arXiv{year_str}"

        # Extract first significant word from venue
        words = re.findall(r'[A-Z][A-Z]+', venue_upper)  # Find acronyms
        if words:
            return f"{words[0]}{year_str}"

        # Fallback: use first letters of first 3 words
        words = venue.split()[:3]
        abbrev = ''.join([w[0].upper() for w in words if w])
        return f"{abbrev}{year_str}" if abbrev else f"{year_str}"

    def add_paper(
        self,
        paper_data: Dict[str, Any],
        pdf_content: Optional[bytes] = None,
        is_internal: bool = False,
    ) -> PaperMetadata:
        """
        Add a paper to storage.

        Args:
            paper_data: Paper metadata dictionary
            pdf_content: Optional PDF file content
            is_internal: Whether this is an internal (manually added) paper

        Returns:
            PaperMetadata object
        """
        # Create metadata object
        paper = PaperMetadata(
            paper_id=paper_data.get("id", self._generate_paper_id(paper_data)),
            title=paper_data.get("title", "Unknown"),
            authors=paper_data.get("authors", []),
            year=paper_data.get("year"),
            abstract=paper_data.get("abstract", ""),
            venue=paper_data.get("venue"),
            conference=paper_data.get("conference"),
            journal=paper_data.get("journal"),
            volume=paper_data.get("volume"),
            pages=paper_data.get("pages"),
            doi=paper_data.get("doi"),
            arxiv_id=paper_data.get("arxiv_id"),
            url=paper_data.get("url"),
            pdf_url=paper_data.get("pdf_url"),
            citations=paper_data.get("citations", 0),
            keywords=paper_data.get("keywords", []),
            topics=paper_data.get("topics", []),
            source=paper_data.get("source", "unknown"),
        )

        # Choose directory
        base_dir = self.internal_dir if is_internal else self.external_dir

        # Create filename: ConferenceYear_ShortTitle
        conf_prefix = self._extract_conference_abbrev(paper_data)

        # Shorten title (max 60 chars)
        short_title = paper.title[:60] if len(paper.title) > 60 else paper.title

        base_filename = self._sanitize_filename(f"{conf_prefix}_{short_title}")

        # Save PDF if provided
        if pdf_content:
            pdf_filename = base_filename + ".pdf"
            pdf_path = base_dir / "pdfs" / pdf_filename
            with open(pdf_path, "wb") as f:
                f.write(pdf_content)
            paper.pdf_path = str(pdf_path)

        # Save metadata with SAME filename as PDF (just .json instead of .pdf)
        metadata_filename = base_filename + ".json"
        metadata_path = base_dir / "metadata" / metadata_filename
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(paper.to_dict(), f, indent=2, ensure_ascii=False)

        # Update index
        if is_internal:
            self.internal_index[paper.paper_id] = paper
        else:
            self.external_index[paper.paper_id] = paper

        self.all_papers[paper.paper_id] = paper

        return paper

    def _generate_paper_id(self, paper_data: Dict[str, Any]) -> str:
        """Generate a unique paper ID from paper data."""
        # Use existing ID if available
        if "id" in paper_data:
            return paper_data["id"]

        # Generate from title + first author + year
        title = paper_data.get("title", "unknown")
        authors = paper_data.get("authors", [])
        year = paper_data.get("year", "")

        first_author = authors[0] if authors else "unknown"
        id_str = f"{title}_{first_author}_{year}"

        # Create hash
        return hashlib.md5(id_str.encode()).hexdigest()[:16]

    def get_paper(self, paper_id: str) -> Optional[PaperMetadata]:
        """Get paper by ID (checks internal first, then external)."""
        # Check internal first (priority)
        if paper_id in self.internal_index:
            return self.internal_index[paper_id]

        # Then check external
        if paper_id in self.external_index:
            return self.external_index[paper_id]

        return None

    def paper_exists(self, paper_id: str) -> bool:
        """Check if paper exists in either collection."""
        return paper_id in self.all_papers

    def search_papers(
        self,
        query: str = None,
        keywords: List[str] = None,
        topics: List[str] = None,
        year_min: int = None,
        year_max: int = None,
        limit: int = 100,
    ) -> List[PaperMetadata]:
        """
        Search papers by various criteria.

        Args:
            query: Text search in title/abstract
            keywords: Filter by keywords
            topics: Filter by topics
            year_min: Minimum publication year
            year_max: Maximum publication year
            limit: Maximum results

        Returns:
            List of matching papers
        """
        results = []

        for paper in self.all_papers.values():
            # Text search (match in title OR abstract OR keywords)
            if query:
                query_lower = query.lower()
                # Split query into words for better matching
                query_words = query_lower.split()

                # Check if ANY query word matches
                title_lower = paper.title.lower()
                abstract_lower = paper.abstract.lower() if paper.abstract else ""

                title_match = any(word in title_lower for word in query_words)
                abstract_match = any(word in abstract_lower for word in query_words)
                keyword_match = any(
                    any(word in kw.lower() for word in query_words)
                    for kw in paper.keywords
                )

                if not (title_match or abstract_match or keyword_match):
                    continue

            # Keyword filter
            if keywords:
                if not any(kw.lower() in [k.lower() for k in paper.keywords] for kw in keywords):
                    continue

            # Topic filter
            if topics:
                if not any(t.lower() in [tp.lower() for tp in paper.topics] for t in topics):
                    continue

            # Year filter
            if year_min and (not paper.year or paper.year < year_min):
                continue

            if year_max and (not paper.year or paper.year > year_max):
                continue

            results.append(paper)

            if len(results) >= limit:
                break

        # Sort by year (descending) and citations
        results.sort(key=lambda p: (p.year or 0, p.citations), reverse=True)

        return results

    def get_all_papers(self, internal_only: bool = False) -> List[PaperMetadata]:
        """Get all papers."""
        if internal_only:
            return list(self.internal_index.values())
        return list(self.all_papers.values())

    def get_statistics(self) -> Dict[str, Any]:
        """Get storage statistics."""
        return {
            "total_papers": len(self.all_papers),
            "internal_papers": len(self.internal_index),
            "external_papers": len(self.external_index),
            "papers_with_pdf": sum(
                1 for p in self.all_papers.values() if p.pdf_path
            ),
        }

    def rebuild_indexes(self):
        """Rebuild all indexes from disk."""
        self._build_indexes()
