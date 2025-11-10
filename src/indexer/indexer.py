"""Paper indexing system for keywords and topics extraction."""

import re
from typing import List, Dict, Any
from collections import Counter


class PaperIndexer:
    """Extract keywords and topics from paper metadata."""

    # Common blockchain/smart contract topics
    BLOCKCHAIN_TOPICS = {
        "smart contract": ["smart contract", "solidity", "ethereum", "evm"],
        "security": ["security", "vulnerability", "exploit", "attack"],
        "reentrancy": ["reentrancy", "re-entrancy", "reentrant"],
        "verification": ["verification", "formal method", "model checking"],
        "testing": ["testing", "fuzzing", "symbolic execution"],
        "analysis": ["static analysis", "dynamic analysis", "program analysis"],
        "blockchain": ["blockchain", "distributed ledger", "consensus"],
        "defi": ["defi", "decentralized finance", "dex", "liquidity"],
        "gas optimization": ["gas", "optimization", "efficiency"],
        "bytecode": ["bytecode", "opcode", "compilation"],
    }

    # Common conferences in blockchain/security
    KNOWN_CONFERENCES = {
        "CCS", "IEEE S&P", "USENIX Security", "NDSS", "SOSP", "OSDI",
        "PLDI", "POPL", "OOPSLA", "ICSE", "FSE", "ASE",
        "Euro S&P", "ACSAC", "RAID", "DSN",
    }

    def extract_keywords(
        self,
        title: str,
        abstract: str,
        existing_keywords: List[str] = None
    ) -> List[str]:
        """
        Extract keywords from title and abstract.

        Args:
            title: Paper title
            abstract: Paper abstract
            existing_keywords: Existing keywords from source

        Returns:
            List of keywords
        """
        keywords = set()

        # Add existing keywords
        if existing_keywords:
            keywords.update(k.lower() for k in existing_keywords)

        # Combine title and abstract
        text = f"{title} {abstract}".lower()

        # Extract domain-specific terms
        # Smart contract patterns
        if re.search(r'\b(smart\s+contract|solidity|ethereum)\b', text):
            keywords.add("smart-contracts")

        if re.search(r'\b(reentrancy|re-entran)', text):
            keywords.add("reentrancy")

        if re.search(r'\b(vulnerability|vulnerabilities|exploit)', text):
            keywords.add("vulnerability")

        if re.search(r'\b(security|secure)\b', text):
            keywords.add("security")

        if re.search(r'\b(verification|formal\s+method)', text):
            keywords.add("verification")

        if re.search(r'\b(testing|fuzzing)\b', text):
            keywords.add("testing")

        if re.search(r'\b(analysis|analyzer)\b', text):
            keywords.add("analysis")

        if re.search(r'\b(blockchain|distributed\s+ledger)\b', text):
            keywords.add("blockchain")

        if re.search(r'\b(defi|decentralized\s+finance)\b', text):
            keywords.add("defi")

        if re.search(r'\b(bytecode|opcode)\b', text):
            keywords.add("bytecode")

        # Extract capitalized terms (likely important concepts)
        # Skip common words
        capitalized = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', f"{title} {abstract}")
        stop_words = {"The", "A", "An", "In", "On", "For", "With", "This", "These", "That"}

        for term in capitalized:
            if term not in stop_words and len(term) > 3:
                keywords.add(term.lower())

        return sorted(list(keywords))

    def extract_topics(
        self,
        title: str,
        abstract: str,
    ) -> List[str]:
        """
        Extract research topics from title and abstract.

        Args:
            title: Paper title
            abstract: Paper abstract

        Returns:
            List of topics
        """
        topics = set()
        text = f"{title} {abstract}".lower()

        # Check against known topics
        for topic, patterns in self.BLOCKCHAIN_TOPICS.items():
            for pattern in patterns:
                if pattern.lower() in text:
                    topics.add(topic)
                    break

        return sorted(list(topics))

    def extract_conference(self, venue: str) -> str:
        """
        Extract conference name from venue string.

        Args:
            venue: Venue string (e.g., "IEEE S&P 2023")

        Returns:
            Conference acronym or cleaned venue name
        """
        if not venue:
            return ""

        # Check for known conferences
        for conf in self.KNOWN_CONFERENCES:
            if conf.lower() in venue.lower():
                return conf

        # Try to extract meaningful conference name
        # Remove year
        cleaned = re.sub(r'\b(19|20)\d{2}\b', '', venue).strip()

        # Remove common prefixes/suffixes
        cleaned = re.sub(r'\b(proceedings of|in|the)\b', '', cleaned, flags=re.IGNORECASE)
        cleaned = cleaned.strip()

        # Take first significant part
        parts = cleaned.split()
        if parts:
            # If it's an acronym (all caps), use it
            if parts[0].isupper() and len(parts[0]) <= 10:
                return parts[0]

        return cleaned[:50]  # Limit length

    def normalize_paper_data(self, paper_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize and enrich paper data with extracted metadata.

        Args:
            paper_data: Raw paper data

        Returns:
            Enriched paper data with keywords, topics, etc.
        """
        title = paper_data.get("title", "")
        abstract = paper_data.get("abstract", "")
        venue = paper_data.get("venue", "")

        # Extract keywords and topics
        existing_keywords = paper_data.get("keywords", [])
        keywords = self.extract_keywords(title, abstract, existing_keywords)
        topics = self.extract_topics(title, abstract)

        # Extract conference
        conference = self.extract_conference(venue)

        # Update paper data
        enriched = paper_data.copy()
        enriched["keywords"] = keywords
        enriched["topics"] = topics

        if conference and not enriched.get("conference"):
            enriched["conference"] = conference

        # Extract arXiv ID if present
        if "arxiv" in enriched.get("source", "").lower():
            paper_id = enriched.get("id", "")
            if "arXiv_" in paper_id:
                arxiv_id = paper_id.replace("arXiv_", "")
                enriched["arxiv_id"] = arxiv_id

        return enriched
