# Literature Review Tool

An automated tool that generates related work sections for research papers using LLMs, multi-source paper retrieval, and intelligent paper management with PDF storage.

## 🌟 Key Features

- **📚 File-Based Storage**: No database required - all papers stored as PDFs + metadata
- **🎯 Two-Tier System**:
  - `papers_internal/` - Manually added papers (high priority)
  - `papers_external/` - Automatically downloaded papers
- **📄 PDF Management**: Automatic download and storage of paper PDFs
- **🏷️ Smart Naming**: Papers named by conference: `ConferenceYear_Title.pdf`
- **📖 BibTeX Generation**: Google Scholar-formatted citations for each paper
- **🔍 Auto-Indexing**: Automatic keyword and topic extraction
- **🤖 LLM-Powered**: Uses Claude or GPT-4 to generate coherent related work sections
- **🔗 Multi-Source**: Searches arXiv, Semantic Scholar, and local storage

## 📦 Installation

1. **Clone or navigate to the project directory**

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Set up environment variables**:
```bash
cp .env.example .env
```

Edit `.env` and add your API keys:
- `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` (required for LLM generation)
- `SEMANTIC_SCHOLAR_API_KEY` (optional but recommended for higher rate limits)

## 🚀 Quick Start

### Basic Usage

Generate a related work section from an abstract:

```bash
python main.py --input examples/example_paper.txt --output related_work.md
```

### With PDF Downloads

```bash
python main.py --input paper.txt --download-pdfs --max-papers 15
```

### Export BibTeX Citations

```bash
python main.py --input paper.txt --export-bibtex citations.bib
```

### Search Only Local Storage (No Network)

```bash
python main.py --input paper.txt --sources local
```

## 📁 Project Structure

```
agent_literature_review/
├── main.py                         # Main CLI application
├── requirements.txt                # Dependencies
├── README.md                       # This file
├── .env                            # Your API keys (create this)
│
├── papers_internal/                # Manually added papers (priority)
│   ├── pdfs/
│   └── metadata/
│
├── papers_external/                # Auto-downloaded papers
│   ├── pdfs/                       # Named as ConferenceYear_Title.pdf
│   └── metadata/                   # JSON files with full metadata + BibTeX
│
├── examples/                       # Example papers
│   ├── example_paper.txt
│   └── blockchain_paper.txt
│
├── tests/                          # Test suite
│   ├── test_config.py
│   ├── test_retrievers.py
│   └── test_generator.py
│
└── src/
    ├── config.py                   # Configuration
    ├── storage.py                  # File-based storage system
    ├── indexer.py                  # Keyword/topic extraction
    ├── pdf_downloader.py           # PDF download utilities
    ├── retrievers/
    │   ├── arxiv_retriever.py      # arXiv API + conference extraction
    │   ├── semantic_scholar.py     # Semantic Scholar API
    │   └── unified_retriever_v2.py # Unified multi-source retrieval
    └── generators/
        └── related_work_generator.py
```

## 🎯 Paper Naming Convention

Papers are automatically named by their **actual published conference**, not arXiv category.

**Format**: `ConferenceYear_ShortTitle.pdf`

**How It Works**:
1. System extracts conference from arXiv metadata (`journal_ref` or `comment` fields)
2. Recognizes patterns like "Accepted at FSE 2024" or "To appear at ICSE 2024"
3. Maps to standard abbreviations for top-tier conferences
4. Only uses arXiv category (e.g., `arXivCSCR24_`) if paper NOT published elsewhere

**Real Examples** (from test run):
- `FSE24_Efficiently_Detecting_Reentrancy_Vulnerabilities_in_Complex.pdf` - Published at FSE 2024
- `ICSE24_Uncover_the_Premeditated_Attacks_Detecting_Exploitable_Reen.pdf` - Published at ICSE 2024
- `IWBOSE21_Reentrancy_Vulnerability_Identification_in_Ethereum_Smart_Co.pdf` - Workshop paper
- `arXivCSCR24_Unity_is_Strength_Enhancing_Precision_in_Reentrancy_Vulnera.pdf` - arXiv-only (cs.CR)

**Recognized Top-Tier Conferences**:
- **Security**: CCS, IEEE S&P (SP), USENIX Security (SEC), NDSS
- **Software Engineering**: ICSE, FSE, ASE, ISSTA, SANER, ICSME
- **Systems**: SOSP, OSDI
- **Programming Languages**: PLDI, POPL, OOPSLA

**Workshop/Unknown Conferences**: Uses acronym as-is (e.g., IWBOSE, DSN)

## 📖 Rich Metadata

Each paper includes a JSON metadata file with:

```json
{
  "paper_id": "arXiv_2105.02881v1",
  "title": "Reentrancy Vulnerability Identification...",
  "authors": ["Author 1", "Author 2"],
  "year": 2021,
  "venue": "arXiv:cs.CR",
  "keywords": ["blockchain", "security", "reentrancy"],
  "topics": ["smart contract", "security", "vulnerability"],
  "pdf_path": "papers_external/pdfs/arXivCSCR21_Reentrancy_Vulnerability....pdf",
  "bibtex": "@inproceedings{Author2021,...}"
}
```

## 💻 Command-Line Options

```bash
python main.py [options]

Required (one of):
  --input, -i PATH         Input file with title/abstract
  --abstract, -a TEXT      Abstract text directly

Optional:
  --title, -t TEXT         Paper title
  --max-papers, -n N       Max papers to retrieve (default: 10)
  --sources [...]          Sources: local, arxiv, semantic_scholar
  --download-pdfs          Download PDFs (default: true)
  --no-download-pdfs       Skip PDF downloads
  --categorized, -c        Generate categorized output with themes
  --style STYLE            Writing style: academic, concise, detailed
  --output, -o PATH        Output file (default: stdout)
  --export-bibtex PATH     Export BibTeX citations
  --show-stats             Show storage statistics
  --llm-provider PROVIDER  LLM to use: openai, anthropic
```

## 📚 How It Works

### Priority System

1. **Check `papers_internal/`** first (manually added papers)
2. **Check `papers_external/`** second (previously downloaded)
3. **Fetch from external sources** (arXiv, Semantic Scholar) if needed
4. **Download PDFs** and save to `papers_external/`
5. **Auto-index** with keywords and topics
6. **Generate BibTeX** citations

### Paper Flow

```
Input Abstract
      ↓
Search papers_internal/ (priority)
      ↓
Search papers_external/ (cache)
      ↓
Fetch from arXiv / Semantic Scholar
      ↓
Download PDFs (ConferenceYear_Title.pdf)
      ↓
Extract keywords & topics
      ↓
Generate BibTeX citations
      ↓
Save to papers_external/
      ↓
Generate related work section
```

## 🔧 Advanced Usage

### Adding Papers Manually

Create a metadata file in `papers_internal/metadata/my_paper.json`:

```json
{
  "paper_id": "my_important_paper",
  "title": "My Important Research",
  "authors": ["Your Name"],
  "year": 2024,
  "abstract": "This paper presents...",
  "keywords": ["blockchain", "security"],
  "topics": ["smart contract"]
}
```

Optionally add PDF to `papers_internal/pdfs/my_paper.pdf`

The tool will automatically prioritize your papers!

### Python API

```python
from src.retrievers.unified_retriever_v2 import UnifiedRetrieverV2
from src.generators.related_work_generator import RelatedWorkGenerator

# Initialize
retriever = UnifiedRetrieverV2(download_pdfs=True)
generator = RelatedWorkGenerator()

# Retrieve papers
papers = retriever.retrieve_related_papers(
    paper_abstract="Your abstract here...",
    max_results=15
)

# Generate related work
related_work = generator.generate_related_work(
    paper_abstract="Your abstract...",
    related_papers=papers
)

# Get statistics
stats = retriever.get_storage_stats()
print(f"Total papers: {stats['total_papers']}")
```

## 📊 Storage Statistics

```bash
python main.py --input paper.txt --show-stats
```

Output:
```
📊 Storage Statistics:
   Total papers: 47
   Internal papers (papers_internal/): 3
   External papers (papers_external/): 44
   Papers with PDFs: 45
```

## 🔍 Search Functionality

### Text Search
Searches title, abstract, and keywords:
```bash
python main.py --abstract "reentrancy vulnerability" --sources local
```

### By Topics
Papers automatically categorized into topics:
- Smart contract
- Security
- Reentrancy
- Verification
- Testing
- Analysis
- Blockchain
- DeFi

## 📝 Example Workflow

```bash
# 1. Initial search with PDF downloads
python main.py \
  --input my_paper.txt \
  --max-papers 20 \
  --download-pdfs \
  --export-bibtex refs.bib \
  --output related_work.md \
  --show-stats

# Output shows:
# - 20 papers downloaded
# - PDFs named as: CCS24_Title.pdf, ICSE23_Title.pdf, etc.
# - BibTeX exported to refs.bib

# 2. Later searches are instant (uses local cache)
python main.py --input another_paper.txt --sources local

# 3. Add your own papers to papers_internal/
# They will be prioritized in future searches!
```

## 🌐 Environment Variables

Edit `.env`:

```bash
# LLM API Keys (choose one)
ANTHROPIC_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here

# Semantic Scholar (optional, for higher rate limits)
SEMANTIC_SCHOLAR_API_KEY=your_key_here

# Settings
LLM_PROVIDER=anthropic                          # or openai
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022      # best for academic writing
MAX_PAPERS=10
DOWNLOAD_PDFS=true
PDF_DOWNLOAD_TIMEOUT=30
```

## 🧪 Testing

```bash
# Quick verification
python verify_setup.py

# Full test suite
./run_tests.sh

# Specific tests
python -m pytest tests/test_config.py -v
```

## 🐛 Troubleshooting

### Papers not downloading
- Check internet connection
- Increase `PDF_DOWNLOAD_TIMEOUT` in `.env`
- Some papers may not have open-access PDFs

### Semantic Scholar 403 error
- Expected without API key (free tier has low limits)
- Get free key at: https://www.semanticscholar.org/product/api

### LLM generation fails
- Check API key in `.env`
- Add credits to your account
- Tool uses fallback generation if LLM fails

### Search finds no local papers
- Run with `--show-stats` to check paper count
- Verify JSON files exist in `papers_*/metadata/`
- Check search query isn't too specific

## 🔑 Key Design Decisions

### Conference-First Naming
Papers are named by their published venue (e.g., `ICSE24_`), NOT by arXiv category. This makes it easier to:
- Organize papers by conference
- Quickly identify paper provenance
- Sort papers naturally by venue + year

### Two-Tier Storage
- `papers_internal/` - Your manually curated papers (always checked first)
- `papers_external/` - Auto-downloaded cache (checked second)

This ensures your important papers are always prioritized in searches.

### File-Based Storage
No database required! Each paper consists of:
- PDF file: `ConferenceYear_Title.pdf`
- Metadata JSON: `ConferenceYear_Title.json` (same base name)

This makes it easy to backup, share, and version control your paper collection.

## 🎓 Academic Use

### BibTeX Citations

Export properly formatted citations:

```bash
python main.py --input paper.txt --export-bibtex citations.bib
```

Import into:
- LaTeX documents
- Overleaf
- Zotero
- Mendeley

### Citation Format

```bibtex
@inproceedings{Samreen2021,
  title={Reentrancy Vulnerability Identification in Ethereum Smart Contracts},
  author={Noama Fatima Samreen and Manar H. Alalfi},
  year={2021},
  booktitle={arXiv:cs.CR},
  url={http://arxiv.org/abs/2105.02881v1}
}
```

## 🚀 Performance

- **Storage**: ~3-5 MB per paper (PDF + metadata)
- **Search**: Instant for local papers (<1ms)
- **PDF Download**: 2-5 seconds per paper
- **LLM Generation**: 10-30 seconds
- **Deduplication**: Automatic (title-based)

## 🔮 Future Enhancements

Planned features:
- Full-text PDF search using embeddings
- Citation graph analysis
- Better duplicate detection
- Topic modeling with ML
- Interactive web interface

## 📄 License

MIT License - feel free to use and modify for your research!

## 🙏 Acknowledgments

- Storage design inspired by [paper-qa](https://github.com/Future-House/paper-qa)
- Uses arXiv and Semantic Scholar APIs
- Powered by Anthropic Claude / OpenAI GPT-4

## 📞 Support

For issues or questions:
- Run `python verify_setup.py` for diagnostics
- Review `TROUBLESHOOTING` section above
- Check example usage in `examples/`

---

**Ready to generate your related work sections!** 🎉

```bash
python main.py --input your_paper.txt --output related_work.md
```
