from mcp.server.fastmcp import FastMCP
import httpx
import xml.etree.ElementTree as ET
import json
import yaml
from fake_useragent import UserAgent
import re
from urllib.parse import unquote
from datetime import datetime
import os
import fitz  # PyMuPDF
from pathlib import Path
from bs4 import BeautifulSoup


mcp = FastMCP("ScholAI MCP Server", version="0.0.0")

proxies = None


async def extract_papers_from_html(html_content, venue=True):
    """
    从HTML内容中提取论文信息
    """
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
        pdf_url = paper_div.find('a', class_='title-pdf')
        if pdf_url:
            onclick_attr = pdf_url.get('onclick', '')
            # 方法1: 处理新格式 - 直接URL (如arxiv)
            # 匹配: togglePdf('id', 'https://arxiv.org/pdf/xxx', this)
            direct_url_match = re.search(r"togglePdf\('[^']*',\s*'([^']+)',", onclick_attr)
            if direct_url_match:
                pdf_url = direct_url_match.group(1)
                # 检查是否是直接的PDF链接
                if pdf_url.startswith('http') and not pdf_url.startswith('/pdf?url='):
                    paper_info['pdf_url'] = pdf_url
                else:
                    # 方法2: 处理旧格式 - 包装的URL
                    # 从 /pdf?url=actual_url 中提取 actual_url
                    actual_url_match = re.search(r'url=([^&]+)', pdf_url)
                    if actual_url_match:
                        paper_info['pdf_url'] = actual_url_match.group(1)

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
                paper_info["publication_time"] = date.get_text(strip=True).split("Publish: ")[-1]

        else:
            subjects_p = paper_div.find("p", class_="metainfo subjects")
            if subjects_p:
                subject_links = subjects_p.find_all("a")
                subjects = [subject.get_text(strip=True) for subject in subject_links]
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




async def load_ccf_ranking() -> dict:
    with open("ccfrank.yml", "r", encoding="utf-8") as f:
        yaml_data = yaml.safe_load(f)

    if not yaml_data or "venues" not in yaml_data:
        print("YAML文件格式不正确或venues列表为空")
        return {}

    ccf_rank_map = {}
    for venue in yaml_data["venues"]:
        rank = venue.get("rank")
        abbr = venue.get("abbr")
        full_name = venue.get("name")

        # 使用缩写和全称作为键
        if abbr:
            ccf_rank_map[abbr.lower()] = rank
        if full_name:
            ccf_rank_map[full_name.lower()] = rank

    return ccf_rank_map

@mcp.tool(name="get_ccf_rank", description="Get the CCF rank of a venue")
async def get_ccf_rank(venue: str) -> str:
    ccf_rank_map = await load_ccf_ranking()
    if venue.lower() in ccf_rank_map:
        return ccf_rank_map[venue.lower()]
    else:
        return "N/A"


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
    response_xml = await httpx.AsyncClient().get(
        f"https://papers.cool/arxiv/search?query={query}&show=1000"
    )
    response_xml.raise_for_status()
    html_content = response_xml.text
    papers = await extract_papers_from_html(html_content, venue=False)

    if need_datetime_sort:
        papers = sorted(
            papers, key=lambda x: x.get("publication_time", 0), reverse=True
        )

    papers = papers[:num_results]

    return papers


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
    response_xml = await httpx.AsyncClient().get(
        f"https://papers.cool/venue/search?query={query}&show=1000"
    )
    response_xml.raise_for_status()
    html_content = response_xml.text
    papers = await extract_papers_from_html(html_content, venue=True)

    if need_datetime_sort:
        papers = sorted(
            papers, key=lambda x: x.get("publication_time", 0), reverse=True
        )

    papers = papers[:num_results]

    return papers


def format_filename(title: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "_", title.strip())[:100] + ".pdf"


@mcp.tool(name="download_paper_pdf", description="Download pdf file of paper from the pdf_url")
async def download_paper_pdf(title: str, pdf_url: str) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.get(pdf_url)
        response.raise_for_status()
        content = response.content

    save_path = format_filename(title)
    with open(f"./data/{save_path}", "wb") as f:
        f.write(content)
    return save_path


@mcp.tool(
    name="extract_academic_query",
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
def extract_academic_query(
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
    result = {
        "step_number": step_number,
        "total_steps": total_steps,
        "next_step_needed": next_step_needed,
        "analysis_step": analysis_step,
        "confidence_level": confidence_level or 0.5,
    }

    if not next_step_needed:
        # Final step: generate complete query
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
        # Intermediate step
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


@mcp.tool(
    name="list_downloaded_papers",
    description="When you need to read a paper, first List all paths of downloaded papers",
)
async def list_downloaded_papers() -> list[str]:
    return [file for file in Path("./data").iterdir() if file.suffix == ".pdf"]


@mcp.tool(name="extract_pdf_text", description="Extract text from a PDF file")
async def extract_pdf_text(pdf_path: str) -> str:
    
    if not Path(pdf_path).exists():
        pdf_path = Path("./data") / pdf_path
        if not pdf_path.exists():
            return "PDF file not found"
        pdf_path = pdf_path.as_posix()
    
    pdf_document = fitz.open(pdf_path)

    full_text = ""

    for page_num in range(len(pdf_document)):
        page = pdf_document[page_num]
        full_text += page.get_text()

    pdf_document.close()

    return full_text


if __name__ == "__main__":
    print("Starting MCP server...")
    mcp.run(transport="stdio")
