# 🎓 ScholAI

**An intelligent academic research assistant powered by Model Context Protocol**

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![MCP](https://img.shields.io/badge/MCP-1.9.4+-green.svg)](https://modelcontextprotocol.io)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

English | [中文](./README.md)

## ✨ Overview

ScholAI is a Model Context Protocol (MCP) server designed to enhance academic research workflows. It provides tools for discovering, analyzing, and managing scholarly publications with features like CCF ranking integration and semantic query analysis.

## 🚀 Key Features

- **🔍 Multi-Database Search**: Access arXiv preprints and peer-reviewed publications
- **🏆 CCF Ranking Integration**: Automatically determine conference and journal rankings
- **📄 PDF Management**: Download and extract text from academic papers
- **🧠 Semantic Query Analysis**: Transform natural language research interests into precise academic queries

## 🛠️ Core Tools

### 📚 Search & Discovery

#### `search_on_arxiv`
Search preprint papers on arXiv repository.

**Parameters:**
- `query`: Search keywords or phrase
- `num_results`: Maximum papers to return (default: 100)
- `need_datetime_sort`: Sort by submission date (default: False)

#### `search_on_venue`
Search academic papers within specific conferences and journals.

**Parameters:**
- `query`: Search keywords or phrase
- `num_results`: Maximum papers to return (default: 100)
- `need_datetime_sort`: Sort by publication date (default: True)

### 📖 Paper Management

#### `get_ccf_rank`
Get the CCF ranking of an academic venue.

**Parameters:**
- `venue`: Name of the conference or journal

#### `download_paper_pdf`
Download and save PDF files locally.

**Parameters:**
- `title`: Paper title for filename generation
- `pdf_url`: Direct PDF download URL

#### `read_paper`
Extract text content from PDF files.

**Parameters:**
- `pdf_path`: Path to PDF file

### 🧭 Research Intelligence

#### `sequential_extract_academic_query`
Progressive analysis tool for transforming research interests into precise queries.

**Parameters:**
- `analysis_step`: Current analysis content
- `step_number`: Current step index
- `total_steps`: Estimated total steps
- `next_step_needed`: Continue analysis flag
- Additional parameters for concepts, databases, search strategy, etc.

#### `list_downloaded_papers`
List all downloaded PDF files in the data directory.

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

- **CCF Rankings**: Place `ccfrank.yml` in the root directory for venue rankings
- **Data Directory**: `./data/` for downloaded PDFs

## 💡 Usage Examples

### Basic Paper Search

```python
# Search for machine learning papers on arXiv
papers = await search_on_arxiv(
    query="machine learning",
    num_results=10
)
```

### Conference-Specific Search

```python
# Find papers from specific venues
papers = await search_on_venue(
    query="neural networks",
    num_results=20,
    need_datetime_sort=True
)
```

### Complete Research Workflow

```python
# 1. Search for papers
papers = await search_on_arxiv("transformer architecture")

# 2. Get CCF ranking for a venue
rank = await get_ccf_rank("ICML")

# 3. Download paper
saved_file = await download_paper_pdf(papers[0]["title"], papers[0]["pdf_url"])

# 4. Extract and read content
content = await read_paper(saved_file)
```

## 🏗️ Technical Architecture

### Core Dependencies

- **FastMCP**: Model Context Protocol server framework
- **httpx**: Asynchronous HTTP client for API requests
- **PyMuPDF (fitz)**: PDF processing and text extraction
- **PyYAML**: Configuration file processing
- **BeautifulSoup**: HTML parsing

### File Structure

```
ScholAI/
├── main.py              # Main MCP server implementation
├── pyproject.toml       # Project configuration
├── uv.lock              # Dependency lock file
├── ccfrank.yml          # CCF ranking database
├── data/                # Downloaded papers storage
└── README.md            # Documentation
```

---

**Built with ❤️ for the academic research community** 