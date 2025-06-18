# 🎓 ScholAI MCP Server

**An intelligent academic research assistant powered by Model Context Protocol**

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![MCP](https://img.shields.io/badge/MCP-1.9.4+-green.svg)](https://modelcontextprotocol.io)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Contributions Welcome](https://img.shields.io/badge/Contributions-Welcome-brightgreen.svg)](CONTRIBUTING.md)

## ✨ Overview

ScholAI is a comprehensive Model Context Protocol (MCP) server designed to revolutionize academic research workflows. It provides intelligent tools for discovering, analyzing, and managing scholarly publications across multiple academic databases with advanced features like CCF ranking integration and semantic query analysis.

### 🚀 Key Features

- **🔍 Multi-Database Search**: Access arXiv preprints and peer-reviewed publications from top conferences/journals
- **🏆 CCF Ranking Integration**: Automatically determine conference and journal rankings using comprehensive CCF database
- **📄 Intelligent PDF Processing**: Download and extract structured text from academic papers
- **🧠 Semantic Query Analysis**: Transform natural language research interests into precise academic queries
- **📊 Publication Analytics**: Get detailed publication metadata including venue information and citation data
- **💾 Research Management**: Organize and track downloaded papers with built-in file management
- **⚡ High-Performance**: Asynchronous processing for efficient batch operations
- **🔗 DBLP Integration**: Enhanced publication information through academic database linkage

## 🛠️ Core Tools

### 📚 Search & Discovery

#### `search_on_arxiv`
Search preprint papers on arXiv, the world's largest open-access repository.

**Key Features:**
- Multi-disciplinary coverage (CS, Physics, Math, Biology, Economics)
- Simple keyword search interface
- Configurable result sorting and filtering
- Direct PDF access links

**Parameters:**
- `query` (str): Search keywords or phrase
- `num_results` (int, default: 100): Maximum papers to return
- `need_pdf_link` (bool, default: True): Include PDF download links
- `need_datetime_sort` (bool, default: False): Sort by submission date
- `need_publication_info` (bool, default: False): Include detailed metadata

#### `search_on_venue`
Search academic papers within specific conferences and journals.

**Key Features:**
- Venue-specific search in curated databases
- Quality-focused peer-reviewed results
- Conference and journal targeting
- Customizable output options

**Parameters:**
- `query` (str): Search keywords or phrase
- `num_results` (int, default: 100): Maximum papers to return
- `need_pdf_link` (bool, default: True): Include PDF download links
- `need_datetime_sort` (bool, default: False): Sort by publication date
- `need_publication_info` (bool, default: False): Include publication metadata

### 📖 Paper Management

#### `get_publication_info`
Retrieve comprehensive publication information with CCF ranking.

**Features:**
- DBLP database integration
- Automatic CCF ranking determination
- Venue and year information
- Author and citation data

**Parameters:**
- `title` (str): Paper title
- `author` (str, optional): Author name for precise matching

#### `get_paper_pdf_link`
Extract direct PDF download links from paper pages.

**Parameters:**
- `cool_paper_id` (str): Paper identifier URL

#### `download_paper_pdf`
Download and save PDF files locally with organized naming.

**Parameters:**
- `title` (str): Paper title for filename generation
- `pdf_link` (str): Direct PDF download URL

#### `extract_pdf_text`
Extract structured text content from PDF files.

**Features:**
- Page-by-page text extraction
- UTF-8 encoding support
- Structured content preservation

**Parameters:**
- `pdf_path` (str): Path to PDF file

### 🧭 Research Intelligence

#### `extract_academic_query`
Progressive analysis tool for transforming research interests into precise queries.

**Capabilities:**
- Intent understanding and domain identification
- Concept extraction and terminology mapping
- Query optimization and strategy selection
- Multi-step analytical process

**Parameters:**
- `analysis_step` (str): Current analysis content
- `step_number` (int): Current step index
- `total_steps` (int): Estimated total steps
- `next_step_needed` (bool): Continue analysis flag
- Additional parameters for extracted concepts, databases, search strategy, etc.

#### `list_downloaded_papers`
Inventory management for local paper collection.

**Returns:** List of all downloaded PDF files in the data directory

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or higher
- uv package manager (recommended) or pip

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/oDaiSuno/ScholAI
   cd ScholAI
   ```

2. **Install dependencies:**
   ```bash
   # Using uv (recommended)
   uv sync
   
   # Or using pip
   pip install -r requirements.txt
   ```

3. **Prepare data directory:**
   ```bash
   mkdir -p data
   ```

4. **Run the MCP server:**
   ```bash
   python main.py
   ```

### Configuration

The server uses the following configuration:

- **Server Name**: ScholAI MCP Server
- **Version**: 0.0.0
- **Transport**: stdio
- **Data Directory**: `./data/` (for downloaded PDFs)
- **CCF Rankings**: `./data/ccfrank.yml` (4000+ venue rankings)

## 💡 Usage Examples

### Basic Paper Search

```python
# Search for machine learning papers on arXiv
result = await search_on_arxiv(
    query="machine learning",
    num_results=10,
    need_pdf_link=True
)
```

### Conference-Specific Search

```python
# Find papers from specific venues
result = await search_on_venue(
    query="neural networks",
    num_results=20,
    need_publication_info=True
)
```

### Complete Research Workflow

```python
# 1. Search for papers
papers = await search_on_arxiv("transformer architecture")

# 2. Get detailed publication info
for paper in papers:
    pub_info = await get_publication_info(
        title=paper["title"], 
        author=paper["author"]
    )
    
# 3. Download interesting papers
pdf_link = await get_paper_pdf_link(paper["cool_paper_id"])
saved_file = await download_paper_pdf(paper["title"], pdf_link)

# 4. Extract and analyze content
content = await extract_pdf_text(f"./data/{saved_file}")
```

### Intelligent Query Construction

```python
# Transform natural language into academic query
analysis = extract_academic_query(
    analysis_step="Analyzing user interest in deep learning applications",
    step_number=1,
    total_steps=3,
    next_step_needed=True,
    extracted_concepts=["deep learning", "computer vision", "neural networks"]
)
```

## 📋 API Reference

### Response Formats

#### Search Results
```json
{
  "cool_paper_id": "https://papers.cool/arxiv/2301.12345",
  "title": "Paper Title",
  "author": "Author Name",
  "summary": "Paper abstract...",
  "updated": "2024-01-15T10:30:00+00:00",
  "pdf_link": "https://arxiv.org/pdf/2301.12345",
  "publication_info": {
    "venue": "ICML",
    "ccf_rank": "A",
    "year": "2024"
  }
}
```

#### Publication Information
```json
{
  "venue": "International Conference on Machine Learning",
  "ccf_rank": "A",
  "year": "2024",
  "journal": "Journal Name",
  "booktitle": "Conference Proceedings"
}
```

#### Query Analysis Result
```json
{
  "step_number": 3,
  "total_steps": 3,
  "next_step_needed": false,
  "analysis_complete": true,
  "query_config": {
    "keywords": ["machine learning", "deep learning", "neural networks"],
    "databases": "arxiv",
    "filters": {
      "date_range": "recent",
      "sort": "relevance"
    }
  },
  "confidence_level": 0.92
}
```

## 🏗️ Technical Architecture

### Core Dependencies

- **FastMCP**: Model Context Protocol server framework
- **httpx**: Asynchronous HTTP client for API requests
- **PyMuPDF (fitz)**: PDF processing and text extraction
- **PyYAML**: Configuration file processing
- **fake-useragent**: HTTP request anonymization

### Data Sources

- **arXiv**: Preprint repository via papers.cool API
- **DBLP**: Academic publication database
- **CCF Rankings**: Comprehensive conference/journal ranking database
- **Venue Databases**: Curated academic publication collections

### File Structure

```
ScholAI/
├── main.py              # Main MCP server implementation
├── pyproject.toml       # Project configuration
├── uv.lock             # Dependency lock file
├── data/               # Data storage directory
│   ├── ccfrank.yml     # CCF ranking database
│   └── *.pdf           # Downloaded papers
└── README.md           # This documentation
```

## 🔧 Advanced Configuration

### Environment Variables

- `HTTP_PROXY`: HTTP proxy configuration (optional)
- `HTTPS_PROXY`: HTTPS proxy configuration (optional)

### Custom Data Directory

Modify the data directory path in `main.py`:

```python
# Change default data directory
DATA_DIR = "./custom_data_path/"
```

### CCF Rankings Update

Replace `./data/ccfrank.yml` with updated ranking data:

```yaml
venues:
  - rank: A
    abbr: ICML
    name: "International Conference on Machine Learning"
    url: /conf/icml
    dblp: /conf/icml/icml
```

## 🔍 Troubleshooting

### Common Issues

1. **PDF Download Failures**
   - Check network connectivity
   - Verify PDF URL accessibility
   - Ensure sufficient disk space

2. **Search Result Limitations**
   - API rate limiting may apply
   - Large result sets may timeout
   - Network connectivity issues

3. **CCF Ranking Not Found**
   - Venue name variations
   - Missing entries in database
   - Case sensitivity issues

### Debug Mode

Enable verbose logging by modifying the server startup:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 🤝 Contributing

We welcome contributions to ScholAI! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### Development Setup

1. Fork the repository
2. Create a feature branch
3. Install development dependencies
4. Run tests
5. Submit a pull request

### Code Standards

- Follow PEP 8 style guidelines
- Add comprehensive docstrings
- Include unit tests for new features
- Update documentation as needed

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Model Context Protocol**: Foundation framework
- **arXiv**: Open access to scientific papers
- **DBLP**: Academic publication database
- **CCF**: Conference and journal ranking system
- **papers.cool**: API access to academic databases

## 📞 Support

For questions, issues, or suggestions:

- 📧 Open an issue on GitHub
- 💬 Join our community discussions
- 📖 Check the documentation wiki

---

**Built with ❤️ for the academic research community**
