#!/usr/bin/env python3
"""
Automatic cleaning script for papers_external/ directory.

For each PDF in pdfs/, checks if a corresponding metadata file exists in metadata/.
If not, creates metadata by parsing the PDF and using PaperIndexer.
After processing all PDFs, deletes metadata files that don't have corresponding PDFs.
"""

import json
import re
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


from src.indexer.indexer import PaperIndexer
from src.utils.storage import PaperStorage


class PDFMetadataExtractor:
    """Extract basic metadata from PDF files."""

    def __init__(self):
        self.indexer = PaperIndexer()

