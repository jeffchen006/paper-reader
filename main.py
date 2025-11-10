#!/usr/bin/env python3
"""
Literature Review Tool - Main CLI Script

This tool generates related work sections for research papers based on their
introduction or abstract.

Features:
- File-based storage with PDFs
- papers_internal/ for manually added papers (priority)
- papers_external/ for automatically downloaded papers
- BibTeX citations in Google Scholar format
- Automatic keyword and topic indexing
- Papers named by conference: ConferenceYear_Title.pdf
"""

import argparse
import sys
from pathlib import Path

from src.retrievers.unified_retriever_v2 import UnifiedRetrieverV2
from src.generators.related_work_generator import RelatedWorkGenerator
from src.config import MAX_PAPERS, DOWNLOAD_PDFS


def read_input_file(file_path: str) -> tuple[str, str]:
    """
    Read paper title and abstract from a file.

    Expected format:
    Title: <title>
    Abstract: <abstract text>

    or just the abstract text.

    Args:
        file_path: Path to input file

    Returns:
        Tuple of (title, abstract)
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read().strip()

    title = None
    abstract = content

    # Try to parse title and abstract
    if content.startswith("Title:"):
        lines = content.split("\n", 1)
        title = lines[0].replace("Title:", "").strip()
        if len(lines) > 1:
            abstract_part = lines[1].strip()
            if abstract_part.startswith("Abstract:"):
                abstract = abstract_part.replace("Abstract:", "").strip()
            else:
                abstract = abstract_part
    elif "Abstract:" in content:
        parts = content.split("Abstract:", 1)
        if parts[0].strip():
            title = parts[0].strip()
        abstract = parts[1].strip()

    return title, abstract


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Generate related work sections from paper abstracts with PDF storage",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate from abstract text
  python main.py --abstract "Smart contracts are programs..." --output related_work.md

  # Generate from file with PDF download
  python main.py --input abstract.txt --output related_work.md --download-pdfs

  # Use categorized output
  python main.py --input abstract.txt --categorized --output related_work.md

  # Search only specific sources
  python main.py --input abstract.txt --sources arxiv semantic_scholar

  # Export BibTeX citations
  python main.py --input abstract.txt --export-bibtex citations.bib

  # View storage statistics
  python main.py --input abstract.txt --show-stats
        """
    )

    # Input options
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--input", "-i",
        type=str,
        help="Input file containing paper title and/or abstract"
    )
    input_group.add_argument(
        "--abstract", "-a",
        type=str,
        help="Paper abstract as string"
    )

    parser.add_argument(
        "--title", "-t",
        type=str,
        help="Paper title (optional, can be included in input file)"
    )

    # Retrieval options
    parser.add_argument(
        "--max-papers", "-n",
        type=int,
        default=MAX_PAPERS,
        help=f"Maximum number of related papers to retrieve (default: {MAX_PAPERS})"
    )

    parser.add_argument(
        "--sources", "-s",
        nargs="+",
        choices=["local", "arxiv", "semantic_scholar"],
        default=["local", "arxiv", "semantic_scholar"],
        help="Sources to search (default: all)"
    )

    parser.add_argument(
        "--download-pdfs",
        action="store_true",
        default=DOWNLOAD_PDFS,
        help="Download PDFs for papers (default: from config)"
    )

    parser.add_argument(
        "--no-download-pdfs",
        action="store_true",
        help="Don't download PDFs"
    )

    # Generation options
    parser.add_argument(
        "--categorized", "-c",
        action="store_true",
        help="Generate categorized related work with thematic sections"
    )

    parser.add_argument(
        "--style",
        type=str,
        choices=["academic", "concise", "detailed"],
        default="academic",
        help="Writing style (default: academic)"
    )

    # Output options
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="Output file path (default: print to stdout)"
    )

    parser.add_argument(
        "--export-bibtex",
        type=str,
        help="Export BibTeX citations to file"
    )

    parser.add_argument(
        "--show-stats",
        action="store_true",
        help="Show storage statistics"
    )

    # LLM options
    parser.add_argument(
        "--llm-provider",
        type=str,
        choices=["openai", "anthropic"],
        help="LLM provider to use (default: from config)"
    )

    args = parser.parse_args()

    # Determine PDF download setting
    download_pdfs = args.download_pdfs
    if args.no_download_pdfs:
        download_pdfs = False

    # Read input
    if args.input:
        title, abstract = read_input_file(args.input)
        if args.title:  # Command-line title overrides file title
            title = args.title
    else:
        title = args.title
        abstract = args.abstract

    if not abstract:
        print("Error: No abstract provided", file=sys.stderr)
        sys.exit(1)

    print("=" * 80)
    print("📚 Literature Review Tool")
    print("=" * 80)
    if title:
        print(f"\n📄 Paper Title: {title}")
    print(f"\n📝 Abstract preview: {abstract[:200]}...")
    print()

    # Initialize retriever with new storage
    retriever = UnifiedRetrieverV2(download_pdfs=download_pdfs)

    # Show stats if requested
    if args.show_stats:
        stats = retriever.get_storage_stats()
        print("\n📊 Storage Statistics:")
        print(f"   Total papers: {stats['total_papers']}")
        print(f"   Internal papers (papers_internal/): {stats['internal_papers']}")
        print(f"   External papers (papers_external/): {stats['external_papers']}")
        print(f"   Papers with PDFs: {stats['papers_with_pdf']}")
        print()

    # Retrieve related papers
    try:
        related_papers = retriever.retrieve_related_papers(
            paper_abstract=abstract,
            paper_title=title,
            max_results=args.max_papers,
            download_pdfs=download_pdfs,
        )

        if not related_papers:
            sys.exit(1)

        print(f"\n📊 Retrieved {len(related_papers)} related papers:")
        for i, paper in enumerate(related_papers, 1):
            pdf_indicator = "📄" if paper.get("pdf_path") else "  "
            print(f"   {pdf_indicator} {i}. {paper.get('title', 'Unknown')} ({paper.get('year', 'n.d.')})")

        # Export BibTeX if requested
        if args.export_bibtex:
            with open(args.export_bibtex, 'w', encoding='utf-8') as f:
                for paper in related_papers:
                    bibtex = paper.get("bibtex", "")
                    if bibtex:
                        f.write(bibtex + "\n\n")
            print(f"\n📖 BibTeX citations exported to: {args.export_bibtex}")

    except Exception as e:
        print(f"\n❌ Error retrieving papers: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

    # Generate related work section
    try:
        generator = RelatedWorkGenerator(llm_provider=args.llm_provider)

        if args.categorized:
            related_work = generator.generate_categorized_related_work(
                paper_abstract=abstract,
                related_papers=related_papers,
                paper_title=title
            )
        else:
            related_work = generator.generate_related_work(
                paper_abstract=abstract,
                related_papers=related_papers,
                paper_title=title,
                style=args.style
            )

        # Output results
        print("\n" + "=" * 80)
        print("📝 Generated Related Work Section")
        print("=" * 80 + "\n")

        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(related_work)
            print(f"✅ Related work section saved to: {output_path}")
            print(f"\nPreview:\n{related_work[:500]}...")
        else:
            print(related_work)

        print("\n" + "=" * 80)
        print("✨ Done!")
        print("=" * 80)

        # Show final stats
        if download_pdfs:
            stats = retriever.get_storage_stats()
            print(f"\n📊 Total papers in storage: {stats['total_papers']} ({stats['papers_with_pdf']} with PDFs)")

    except Exception as e:
        print(f"\n❌ Error generating related work: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
