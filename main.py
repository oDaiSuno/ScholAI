from mcp.server.fastmcp import FastMCP
import httpx
import xml.etree.ElementTree as ET
import json
import yaml
import re
import fitz
from pathlib import Path
from bs4 import BeautifulSoup
import os
import asyncio

mcp = FastMCP("ScholAI MCP Server", version="0.0.1")

proxies = None


async def extract_papers_from_html(html_content, venue=True):
    """
    从HTML内容中提取论文信息
    """
    try:
        if not html_content or not html_content.strip():
            return []

        soup = BeautifulSoup(html_content, "html.parser")
        papers = []

        # 找到所有论文div
        paper_divs = soup.find_all("div", class_="panel paper")

        for paper_div in paper_divs:
            paper_info = {}

            # 提取标题
            title_link = paper_div.find("a", class_="title-link")
            if title_link:
                paper_info["title"] = title_link.get_text(strip=True)
            pdf_url = paper_div.find("a", class_="title-pdf")
            if pdf_url:
                onclick_attr = pdf_url.get("onclick", "")
                # 方法1: 处理新格式 - 直接URL (如arxiv)
                # 匹配: togglePdf('id', 'https://arxiv.org/pdf/xxx', this)
                direct_url_match = re.search(
                    r"togglePdf\('[^']*',\s*'([^']+)',", onclick_attr
                )
                if direct_url_match:
                    pdf_url = direct_url_match.group(1)
                    # 检查是否是直接的PDF链接
                    if pdf_url.startswith("http") and not pdf_url.startswith(
                        "/pdf?url="
                    ):
                        paper_info["pdf_url"] = pdf_url
                    else:
                        # 方法2: 处理旧格式 - 包装的URL
                        # 从 /pdf?url=actual_url 中提取 actual_url
                        actual_url_match = re.search(r"url=([^&]+)", pdf_url)
                        if actual_url_match:
                            paper_info["pdf_url"] = actual_url_match.group(1)

            # 提取第一作者
            authors_p = paper_div.find("p", id=lambda x: x and x.startswith("authors-"))
            if authors_p:
                # 查找所有作者链接
                author_links = authors_p.find_all("a", class_="author")
                if author_links:
                    # 只保留第一作者
                    first_author = author_links[0].get_text(strip=True)
                    paper_info["first_author"] = first_author
                else:
                    # 如果没有找到author类的链接，尝试从文本中提取
                    authors_text = authors_p.get_text(strip=True)
                    # 移除"Authors:"前缀，然后按逗号分割取第一个
                    if "Authors:" in authors_text:
                        authors_clean = authors_text.replace("Authors:", "").strip()
                        first_author = authors_clean.split(",")[0].strip()
                        paper_info["first_author"] = first_author

            # 提取摘要
            summary_p = paper_div.find("p", class_="summary")
            if summary_p:
                paper_info["abstract"] = summary_p.get_text(strip=True)

            # 提取出版年份
            publication_time = None

            if not venue:
                date = paper_div.find("p", class_="metainfo date")
                if date:
                    paper_info["publication_time"] = date.get_text(strip=True).split(
                        "Publish: "
                    )[-1]

            else:
                subjects_p = paper_div.find("p", class_="metainfo subjects")
                if subjects_p:
                    subject_links = subjects_p.find_all("a")
                    subjects = [
                        subject.get_text(strip=True) for subject in subject_links
                    ]
                    paper_info["subjects"] = subjects

                    for subject in subjects:
                        year_match = re.search(r"\.(\d{4})", subject)
                        if year_match:
                            publication_time = int(year_match.group(1))
                            break

                if publication_time:
                    paper_info["publication_time"] = publication_time

            papers.append(paper_info)

        return papers
    except Exception as e:
        return [{"error": f"Failed to parse HTML content: {str(e)}"}]


async def load_ccf_ranking() -> dict:
    try:
        with open("ccfrank.yml", "r", encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f)

        if not yaml_data or "venues" not in yaml_data:
            return {}

        ccf_rank_map = {}
        for venue in yaml_data["venues"]:
            rank = venue.get("rank")
            abbr = venue.get("abbr")
            full_name = venue.get("name")

            if abbr:
                ccf_rank_map[abbr.lower()] = rank
            if full_name:
                ccf_rank_map[full_name.lower()] = rank

        return ccf_rank_map
    except FileNotFoundError:
        return {}
    except yaml.YAMLError:
        return {}
    except Exception:
        return {}


@mcp.tool(name="get_ccf_rank", description="Get the CCF rank of a venue")
async def get_ccf_rank(venue: str) -> str:
    try:
        if not venue or not venue.strip():
            return "Error: Venue name cannot be empty"

        ccf_rank_map = await load_ccf_ranking()
        return ccf_rank_map.get(venue.lower(), "N/A")
    except Exception as e:
        return f"Error: Failed to get CCF rank - {str(e)}"


@mcp.tool(
    name="search_on_arxiv",
    description="""
    
    **Query Format**: Use simple keywords only - no boolean operators (AND/OR) supported.
    Examples: "machine learning", "neural networks", "quantum computing"
    
    Search preprint papers on arXiv, the world's largest open-access repository.
    
    This tool searches arXiv's collection of preprint papers across multiple scientific disciplines. Perfect for discovering cutting-edge research before peer review and tracking emerging trends.
    
    Key features:
    - Access to latest research developments before formal publication
    - Multi-disciplinary coverage (physics, math, CS, biology, economics)
    - Simple keyword search (no boolean operators like AND/OR)
    - Open access with immediate PDF availability
    
    Parameters:
    - query: Single search term or phrase
    - num_results: Max papers to return (default: 100)
    - need_datetime_sort: Sort by submission date, newest first (default: False)

    
    Returns: List of preprints with titles, authors, arXiv categories, and optional PDF links.
    """,
)
async def search_on_arxiv(
    query: str,
    num_results: int = 100,
    need_datetime_sort: bool = False,
) -> list:
    try:
        if not query or not query.strip():
            return [{"error": "Query cannot be empty"}]

        if num_results <= 0:
            return [{"error": "Number of results must be positive"}]

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"https://papers.cool/arxiv/search?query={query}&show=1000"
            )
            response.raise_for_status()

        papers = await extract_papers_from_html(response.text, venue=False)

        if need_datetime_sort:
            papers = sorted(
                papers, key=lambda x: x.get("publication_time", 0), reverse=True
            )

        return papers[:num_results]
    except httpx.RequestError as e:
        return [{"error": f"Network request failed: {str(e)}"}]
    except httpx.HTTPStatusError as e:
        return [
            {"error": f"HTTP error {e.response.status_code}: {e.response.text[:100]}"}
        ]
    except Exception as e:
        return [{"error": f"Search failed: {str(e)}"}]


@mcp.tool(
    name="search_on_venue",
    description="""
    
    **Query Format**: Use simple keywords only - no boolean operators (AND/OR) supported.
    Examples: "machine learning", "neural networks", "quantum computing"
    
    Search academic papers within specific conferences and journals (venues).
    
    This tool targets peer-reviewed publications from established academic venues like conferences (NeurIPS, ICML) and journals (Nature, IEEE). Ideal for finding high-quality papers within specific academic communities.
    
    Key features:
    - Venue-specific search within curated conference/journal databases
    - Simple keyword search (no boolean operators like AND/OR)
    - Quality-focused results from peer-reviewed sources
    - Customizable output with PDF links and publication metadata
    
    Parameters:
    - query: Single search term or phrase
    - num_results: Max papers to return (default: 100)
    - need_datetime_sort: Sort by publication date, newest first (default: True)

    
    Returns: List of papers with titles, authors, venue details, and optional PDF links.
    """,
)
async def search_on_venue(
    query: str, num_results: int = 100, need_datetime_sort: bool = True
) -> list:
    try:
        if not query or not query.strip():
            return [{"error": "Query cannot be empty"}]

        if num_results <= 0:
            return [{"error": "Number of results must be positive"}]

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"https://papers.cool/venue/search?query={query}&show=1000"
            )
            response.raise_for_status()

        papers = await extract_papers_from_html(response.text, venue=True)

        if need_datetime_sort:
            papers = sorted(
                papers, key=lambda x: x.get("publication_time", 0), reverse=True
            )

        return papers[:num_results]
    except httpx.RequestError as e:
        return [{"error": f"Network request failed: {str(e)}"}]
    except httpx.HTTPStatusError as e:
        return [
            {"error": f"HTTP error {e.response.status_code}: {e.response.text[:100]}"}
        ]
    except Exception as e:
        return [{"error": f"Search failed: {str(e)}"}]


def format_filename(title: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "_", title.strip())[:100] + ".pdf"


@mcp.tool(
    name="download_paper_pdf",
    description="Download pdf file of paper from the pdf_url. And return the path of the downloaded paper.",
)
async def download_paper_pdf(title: str, pdf_url: str) -> str:
    try:
        if not title or not title.strip():
            return "Error: Title cannot be empty"

        if not pdf_url or not pdf_url.startswith(("http://", "https://")):
            return "Error: Invalid PDF URL"

        # Ensure data directory exists
        data_dir = Path("./data")
        data_dir.mkdir(exist_ok=True)

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(pdf_url)
            response.raise_for_status()

        save_path = format_filename(title)
        file_path = data_dir / save_path

        with open(file_path, "wb") as f:
            f.write(response.content)

        return save_path

    except httpx.RequestError as e:
        return f"Error: Network request failed - {str(e)}"
    except httpx.HTTPStatusError as e:
        return f"Error: HTTP error {e.response.status_code}"
    except OSError as e:
        return f"Error: File operation failed - {str(e)}"
    except Exception as e:
        return f"Error: Download failed - {str(e)}"


@mcp.tool(
    name="sequential_extract_academic_query",
    description="""
    Note: All processes and results must be in English!
    A tool for progressively analyzing and extracting users' academic search intent  

    This tool helps transform vague user expressions into precise academic search queries. Through a multi-step analytical process, it deeply understands users' genuine research needs.  

    Use cases:  
    - When users express ambiguous or overly broad research interests  
    - Converting natural language into academic keywords  
    - Determining optimal search strategies and database selection  
    - Optimizing queries for the most relevant results  
    - Handling interdisciplinary or emerging field search needs  

    Analysis steps include:  
    1. Intent understanding: Parsing core research interests  
    2. Domain identification: Determining primary/secondary research fields  
    3. Concept extraction: Identifying key technical terms and concepts  
    4. Query construction: Combining keywords to form search queries  
    5. Strategy optimization: Selecting appropriate search strategies and filters  
    6. Validation refinement: Verifying query completeness and accuracy  

    Parameter specifications:  
    - analysis_step: Current step's detailed content and reasoning  
    - step_number: Current step index  
    - total_steps: Estimated total steps (adjustable)  
    - next_step_needed: Whether further analysis is required  
    - extracted_concepts: List of identified key concepts  
    - databases: Search databases (options: arxiv, venue)  
    - search_strategy: Recommended search approach  
    - confidence_level: Analysis confidence score (0-1)  
    - needs_clarification: Whether user clarification is needed  
    - clarification_questions: List of follow-up questions for users  
    - date_range: Timeframe (options: recent, all)  
    - datetime_sort: Time-based sorting (options: True, False)  

    Output format:  
    Returns JSON containing:  
    - Generated search queries  
    - Recommended databases/tools  
    - Search parameter configurations  
    - Analysis confidence level  
    - Potential query variations
    """,
)
def sequential_extract_academic_query(
    analysis_step: str,
    step_number: int,
    total_steps: int,
    next_step_needed: bool,
    extracted_concepts: list[str] = None,
    databases: str = None,
    search_strategy: str = None,
    confidence_level: float = None,
    needs_clarification: bool = False,
    clarification_questions: list[str] = None,
    date_range: str = None,
    datetime_sort: bool = False,
) -> str:
    try:
        if not analysis_step or step_number <= 0 or total_steps <= 0:
            return json.dumps({"error": "Invalid parameters provided"})

        result = {
            "step_number": step_number,
            "total_steps": total_steps,
            "next_step_needed": next_step_needed,
            "analysis_step": analysis_step,
            "confidence_level": confidence_level or 0.5,
        }

        if not next_step_needed:
            concepts = extracted_concepts or []
            result.update(
                {
                    "query_config": {
                        "keywords": concepts[:3],
                        "databases": databases,
                        "filters": {
                            "date_range": date_range,
                            "sort": "datetime" if datetime_sort else "relevance",
                        },
                    },
                    "alternatives": (
                        [{"keywords": concepts[3:6]}] if len(concepts) > 3 else []
                    ),
                    "analysis_complete": True,
                }
            )
        else:
            result.update(
                {
                    "extracted_concepts": extracted_concepts or [],
                    "databases": databases,
                    "search_strategy": search_strategy,
                    "needs_clarification": needs_clarification,
                    "clarification_questions": clarification_questions or [],
                }
            )

        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Query extraction failed: {str(e)}"})


@mcp.tool(
    name="list_downloaded_papers",
    description="When you need to read a paper, first List all paths of downloaded papers. ",
)
async def list_downloaded_papers() -> list[str]:
    try:
        data_dir = Path("./data")
        if not data_dir.exists():
            return ["Error: Data directory does not exist"]

        pdf_files = [file.name for file in data_dir.iterdir() if file.suffix == ".pdf"]
        return pdf_files if pdf_files else ["No PDF files found"]
    except PermissionError:
        return ["Error: Permission denied accessing data directory"]
    except Exception as e:
        return [f"Error: Failed to list files - {str(e)}"]


async def upload_file_to_llamaparse(
    file_path: str | Path,
    token: str,
    compact_markdown_table: bool = True,
    extract_charts: bool = True,
    structured_output: bool = True,
) -> httpx.Response:
    """
    Uploads a file to the LlamaParse API, converting a cURL command to an httpx function.

    Args:
        file_path: The local path to the file to be uploaded.
        token: The API bearer token for authentication.
        compact_markdown_table: Flag to enable compact markdown table parsing.
        extract_charts: Flag to enable chart extraction.
        structured_output: Flag to enable structured output.

    Returns:
        The response object from the httpx request.
    """
    url = "https://api.cloud.llamaindex.ai/api/v1/parsing/upload"
    headers = {"Accept": "application/json", "Authorization": f"Bearer {token}"}
    data = {
        "compact_markdown_table": str(compact_markdown_table).lower(),
        "extract_charts": str(extract_charts).lower(),
        "structured_output": str(structured_output).lower(),
    }

    async with httpx.AsyncClient(timeout=600.0) as client:
        with open(file_path, "rb") as f:
            files = {"file": f}
            response = await client.post(url, headers=headers, data=data, files=files)
            # Raise an exception for bad status codes (4xx or 5xx)
            response.raise_for_status()
            return response.json()


async def get_job_status(job_id: str, token: str) -> httpx.Response:
    """Gets the parsing job status."""
    url = f"https://api.cloud.llamaindex.ai/api/v1/parsing/job/{job_id}"
    headers = {"Accept": "application/json", "Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        return response


async def get_job_result_markdown(job_id: str, token: str) -> httpx.Response:
    """Gets the parsing job result in markdown format."""
    url = f"https://api.cloud.llamaindex.ai/api/v1/parsing/job/{job_id}/result/markdown"
    headers = {"Accept": "application/json", "Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        return response.json()


async def read_paper_with_llamaindex(pdf_path: str) -> str:
    try:
        if not pdf_path:
            return "Error: PDF path cannot be empty"

        LLAMAINDEX_API_KEY = os.getenv("LLAMAINDEX_API_KEY", None)
        if LLAMAINDEX_API_KEY:
            upload_response = await upload_file_to_llamaparse(
                pdf_path, LLAMAINDEX_API_KEY
            )
            job_id = upload_response.get("id")

            # Step 2: Poll for job completion
            terminal_states = {"SUCCESS", "ERROR"}

            # Get initial job status
            job_response = await get_job_status(job_id, LLAMAINDEX_API_KEY)
            job_json = job_response.json()
            status = job_json.get("status")

            # Poll until job reaches a terminal state
            while status not in terminal_states:
                await asyncio.sleep(5)  # Wait before polling again
                job_response = await get_job_status(job_id, LLAMAINDEX_API_KEY)
                job_json = job_response.json()
                status = job_json.get("status")

            if status == "SUCCESS":
                result_response = await get_job_result_markdown(
                    job_id, LLAMAINDEX_API_KEY
                )

                return result_response.get("markdown", "")
            else:
                return "Error: Failed to read paper"

        else:
            return "Error: LLAMAINDEX_API_KEY is not set"
    except Exception as e:
        return f"Error: Failed to read paper - {str(e)}"


@mcp.tool(name="read_paper", description="You can read the paper by this tool.")
async def read_paper(pdf_path: str) -> str:
    try:
        if not pdf_path:
            return "Error: PDF path cannot be empty"

        # Try original path first, then data directory
        path = Path(pdf_path)
        if not path.exists():
            path = Path("./data") / pdf_path
            if not path.exists():
                return "Error: PDF file not found"

        LLAMAINDEX_API_KEY = os.getenv("LLAMAINDEX_API_KEY", None)
        if LLAMAINDEX_API_KEY:
            return await read_paper_with_llamaindex(path)

        pdf_document = fitz.open(path)
        full_text = ""

        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            full_text += page.get_text()

        pdf_document.close()

        return (
            {"Paper Content": full_text}
            if full_text.strip()
            else "Error: No text content found in PDF"
        )

    except Exception as e:
        return f"Error: Failed to extract text - {str(e)}"


@mcp.tool(
    name="plan_for_paper_search",
    description="This is a tool designed to plan for paper search based on the user query",
)
def plan_for_paper_search(user_query: str, need_intent_extraction: bool) -> str:

    if need_intent_extraction:
        user_query = analyze_user_query(user_query)
        return f"You must combine the following prompt with the `sequential_extract_academic_query` tool to extract the user's true intent, :\n{user_query}"

    return f"You can directly use the `search_on_venue` or `search_on_arxiv` tools to search for papers according to the guidelines."


def analyze_user_query(user_query: str) -> str:

    prompt = f"""
    <prompt>
        <role>
            You are an academic paper search expert. Your task is to extract a single optimal high-level query term from user queries for academic paper searching.
        </role>
        
        <core_principles>
            <principle name="conceptual_generalization">
            Extract abstract academic concepts from specific application scenarios
            </principle>
            <principle name="maximum_coverage">
            Select keywords that can retrieve the most relevant papers
            </principle>
            <principle name="academic_standards">
            Use terminology widely recognized in academic communities
            </principle>
            <principle name="single_output">
            Return only one optimal query term or phrase
            </principle>
        </core_principles>
        
        <extraction_strategies>
            <strategy>Identify the core technical domain or research direction of the user query</strategy>
            <strategy>Abstract specific tools and product names into technical categories</strategy>
            <strategy>Prioritize terms with high frequency in academic literature</strategy>
            <strategy>Consider related higher-level concepts and interdisciplinary fields</strategy>
        </extraction_strategies>
        
        <examples>
            <example>
            <input>paper writing agent</input>
            <output>AI agent</output>
            </example>
            <example>
            <input>code review tool</input>
            <output>software engineering</output>
            </example>
            <example>
            <input>stock price prediction model</input>
            <output>financial forecasting</output>
            </example>
            <example>
            <input>chatgpt for education</input>
            <output>educational technology</output>
            </example>
            <example>
            <input>blockchain voting system</input>
            <output>blockchain</output>
            </example>
            <example>
            <input>autonomous vehicle safety</input>
            <output>autonomous vehicles</output>
            </example>
        </examples>
        
        <output_format>
            Return only the extracted query term without explanation or additional content.
        </output_format>
        
        <user_query>{user_query}</user_query>
        
        <instruction>
            Extract the optimal query term:
        </instruction>
    </prompt>
    """

    return prompt


if __name__ == "__main__":
    print("Starting MCP server...")
    mcp.run(transport="stdio")
