"""PDF downloader for papers."""

import requests
import time
from typing import Optional
from pathlib import Path


class PDFDownloader:
    """Download PDFs from various sources."""

    def __init__(self, timeout: int = 30, max_retries: int = 3):
        """Initialize PDF downloader."""
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def download(self, url: str) -> Optional[bytes]:
        """
        Download PDF from URL.

        Args:
            url: PDF URL

        Returns:
            PDF content as bytes, or None if download fails
        """
        if not url:
            return None

        for attempt in range(self.max_retries):
            try:
                response = self.session.get(url, timeout=self.timeout, stream=True)

                if response.status_code == 200:
                    # Check if it's actually a PDF
                    content_type = response.headers.get('Content-Type', '')
                    if 'pdf' not in content_type.lower():
                        # Still try to download, might be mis-labeled
                        pass

                    # Read content
                    pdf_content = response.content

                    # Verify it starts with PDF header
                    if pdf_content[:4] == b'%PDF':
                        print(f"   ✓ Downloaded PDF ({len(pdf_content) / 1024:.1f} KB)")
                        return pdf_content
                    else:
                        print(f"   ⚠ Downloaded file is not a valid PDF")
                        return None

                elif response.status_code == 403:
                    print(f"   ⚠ Access forbidden (403) for {url}")
                    return None

                elif response.status_code == 404:
                    print(f"   ⚠ PDF not found (404) for {url}")
                    return None

                else:
                    print(f"   ⚠ HTTP {response.status_code} for {url}")

            except requests.exceptions.Timeout:
                print(f"   ⚠ Timeout downloading PDF (attempt {attempt + 1}/{self.max_retries})")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff

            except Exception as e:
                print(f"   ⚠ Error downloading PDF: {e}")
                return None

        return None

    def download_arxiv(self, arxiv_id: str) -> Optional[bytes]:
        """
        Download PDF from arXiv.

        Args:
            arxiv_id: arXiv ID (e.g., '2103.00020')

        Returns:
            PDF content as bytes
        """
        # Clean arXiv ID (remove version if present)
        clean_id = arxiv_id.split('v')[0] if 'v' in arxiv_id else arxiv_id

        url = f"https://arxiv.org/pdf/{clean_id}.pdf"
        return self.download(url)

    def download_to_file(self, url: str, output_path: Path) -> bool:
        """
        Download PDF and save to file.

        Args:
            url: PDF URL
            output_path: Path to save PDF

        Returns:
            True if successful, False otherwise
        """
        pdf_content = self.download(url)

        if pdf_content:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(pdf_content)
            return True

        return False
