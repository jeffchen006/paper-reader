"""Configuration management for the literature review tool."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = os.getenv("DB_PATH", str(DATA_DIR / "papers.db"))  # Legacy, kept for backwards compatibility

# New storage paths
PAPERS_INTERNAL_DIR = PROJECT_ROOT / "papers_internal"
PAPERS_EXTERNAL_DIR = PROJECT_ROOT / "papers_external"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
PAPERS_INTERNAL_DIR.mkdir(exist_ok=True)
PAPERS_EXTERNAL_DIR.mkdir(exist_ok=True)

# LLM Configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "anthropic").lower()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4-turbo-preview")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")

# API Keys
SEMANTIC_SCHOLAR_API_KEY = os.getenv("SEMANTIC_SCHOLAR_API_KEY")

# Retrieval settings
MAX_PAPERS = int(os.getenv("MAX_PAPERS", "10"))

# PDF download settings
DOWNLOAD_PDFS = os.getenv("DOWNLOAD_PDFS", "true").lower() == "true"
PDF_DOWNLOAD_TIMEOUT = int(os.getenv("PDF_DOWNLOAD_TIMEOUT", "30"))

# Semantic Scholar API settings
SEMANTIC_SCHOLAR_BASE_URL = "https://api.semanticscholar.org/graph/v1"
SEMANTIC_SCHOLAR_RATE_LIMIT = 1.0  # seconds between requests

# arXiv settings
# No hardcoded limit - arXiv will fetch as many papers as needed


def get_llm_config():
    """Get the LLM configuration based on provider."""
    if LLM_PROVIDER == "openai":
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not set in environment")
        return {
            "provider": "openai",
            "api_key": OPENAI_API_KEY,
            "model": OPENAI_MODEL
        }
    elif LLM_PROVIDER == "anthropic":
        if not ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY not set in environment")
        return {
            "provider": "anthropic",
            "api_key": ANTHROPIC_API_KEY,
            "model": ANTHROPIC_MODEL
        }
    else:
        raise ValueError(f"Unknown LLM provider: {LLM_PROVIDER}")
