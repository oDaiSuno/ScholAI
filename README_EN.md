# 🎓 ScholAI

**An intelligent academic research assistant powered by MCP v0.0.1**

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![MCP](https://img.shields.io/badge/MCP-1.9.4+-green.svg)](https://modelcontextprotocol.io)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

English | [中文](./README.md)

## ✨ Overview

ScholAI is a Model Context Protocol (MCP) server designed to enhance academic research workflows. It provides tools for discovering, analyzing, and managing scholarly publications with features like CCF ranking integration and semantic query analysis.

![image-20250625172529710](images/image-20250625172529710.png)

![](images/image.png)

## 🆕 v0.0.1 Release Updates

- **🔍 LlamaIndex API Integration** - Enhanced PDF parsing with support for tables and charts extraction
- **🧠 Intelligent Search Planning** - New `plan_for_paper_search` tool for smart research strategy planning
- **🎯 Query Intent Analysis** - Improved understanding of academic queries with core research intent extraction
- **📂 File Management Optimization** - Enhanced PDF file path handling for better file discovery
- **🚀 Performance Improvements** - Optimized async processing and API call logic for faster response times

## 🚀 Quick Start

### Prerequisites

- Python 3.11 or higher
- uv package manager (**recommended**) or pip

### Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/oDaiSuno/ScholAI
   cd ScholAI
   ```

2. **Install dependencies (strongly recommend using uv):**

   ```bash
   # Using uv (recommended)
   uv sync
   
   # Or using pip
   pip install -r requirements.txt
   
   # If the above methods fail, you can manually install missing dependencies
   pip install httpx pyyaml beautifulsoup4 dict2xml mcp[cli] pymupdf
   ```

3. **Prepare data directory:**

   ```bash
   mkdir -p data
   ```

### Configuring MCP Server

Here's an example using Cherry Studio: fill in the name as `ScholAI`, command as `uv`, and parameters as follows (remember to change the project path):

```
--directory
D:\path\to\your\ScholAI
run
main.py
```

### Configuring LlamaIndex API (Optional but Recommended)

For enhanced PDF parsing results, you can set up the `LLAMAINDEX_API_KEY` environment variable:
You can sign up for an account at [llamaindex](https://cloud.llamaindex.ai), create an API Key, and enjoy **10,000 free credits per month**.

![image-20250625170320380](images/image-20250625170320380.png)

![image-20250623182123300](images/image-20250623182123300.png)

## 🍟 Key Features

- **🔍 Multi-Database Search**: Access arXiv preprints and peer-reviewed publications
- **🏆 CCF Ranking Integration**: Automatically determine conference and journal rankings
- **📄 PDF Management**: Download and extract text from academic papers
- **🧠 Semantic Query Analysis**: Transform natural language research interests into precise academic queries
- **📊 Advanced PDF Parsing**: Support for tables and chart extraction via LlamaIndex API (requires API key)

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

#### `plan_for_paper_search`
Plan paper search strategy based on user query.

**Parameters:**
- `user_query`: Original user query
- `need_intent_extraction`: Whether intent extraction is needed (default: True)

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
Extract text content from PDF files with LlamaIndex API enhanced parsing.

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

### Configuration

- **CCF Rankings**: Place `ccfrank.yml` in the root directory for venue rankings
- **Data Directory**: `./data/` for downloaded PDFs
- **LlamaIndex API**: Set environment variable `LLAMAINDEX_API_KEY` to enable advanced PDF parsing

## 🏗️ Technical Architecture

### Core Dependencies

- **FastMCP**: Model Context Protocol server framework
- **httpx**: Asynchronous HTTP client for API requests
- **PyMuPDF (fitz)**: PDF processing and text extraction
- **PyYAML**: Configuration file processing
- **BeautifulSoup**: HTML parsing
- **LlamaIndex API**: Advanced PDF parsing and structured extraction (optional)

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

## 🪻 Special Thanks
- Paper search website: https://papers.cool
- MCP debugging tool: https://kirigaya.cn/openmcp

---

**Star this project to show your support**

[![Star History Chart](https://api.star-history.com/svg?repos=oDaiSuno/ScholAI&type=Date)](https://www.star-history.com/#oDaiSuno/ScholAI&Date) 