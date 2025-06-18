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

mcp = FastMCP("ScholAI MCP Server", version="0.0.0")

proxies = None


async def extract_entries_data(xml_response):
    # 解析XML
    root = ET.fromstring(xml_response)

    # 定义命名空间
    namespaces = {"atom": "http://www.w3.org/2005/Atom"}

    # 提取所有entry元素
    entries = root.findall(".//atom:entry", namespaces)

    extracted_data = []
    for entry in entries:
        # 提取id和title
        entry_id = entry.find("atom:id", namespaces)
        entry_title = entry.find("atom:title", namespaces)
        entry_summary = entry.find("atom:summary", namespaces)
        entry_updated = entry.find("atom:updated", namespaces)
        entry_author = entry.find("atom:author", namespaces).find(
            "atom:name", namespaces
        )

        data = {
            "cool_paper_id": entry_id.text if entry_id is not None else None,
            "title": entry_title.text if entry_title is not None else None,
            "author": entry_author.text if entry_author is not None else None,
            "summary": entry_summary.text if entry_summary is not None else None,
            "updated": entry_updated.text if entry_updated is not None else None,
        }
        extracted_data.append(data)

    return extracted_data


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
    - need_pdf_link: Include PDF download links (default: True)
    - need_datetime_sort: Sort by submission date, newest first (default: False)
    - need_publication_info: Include detailed submission metadata (default: False)
    
    Returns: List of preprints with titles, authors, arXiv categories, and optional PDF links.
    """,
)
async def search_on_arxiv(
    query: str,
    num_results: int = 100,
    need_pdf_link: bool = True,
    need_datetime_sort: bool = False,
    need_publication_info: bool = False,
) -> list:
    response_xml = await httpx.AsyncClient().get(
        f"https://papers.cool/arxiv/search/feed?query={query}"
    )
    response_xml.raise_for_status()
    response_json = await extract_entries_data(response_xml.text)
    if need_datetime_sort:
        response_json = sorted(
            response_json,
            key=lambda x: datetime.fromisoformat(x["updated"]),
            reverse=True,
        )
    response_json = response_json[:num_results]

    for item in response_json:
        if need_publication_info:
            item["publication_info"] = await get_publication_info(
                item["title"], item["author"]
            )
        if need_pdf_link:
            item["pdf_link"] = await get_paper_pdf_link(item["cool_paper_id"])

    return response_json


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
    - need_pdf_link: Include PDF download links (default: True)
    - need_datetime_sort: Sort by publication date, newest first (default: False)
    - need_publication_info: Include detailed publication metadata (default: False)
    
    Returns: List of papers with titles, authors, venue details, and optional PDF links.
    """,
)
async def search_on_venue(
    query: str,
    num_results: int = 100,
    need_pdf_link: bool = True,
    need_datetime_sort: bool = False,
    need_publication_info: bool = False,
) -> list:
    response_xml = await httpx.AsyncClient().get(
        f"https://papers.cool/venue/search/feed?query={query}"
    )
    response_xml.raise_for_status()
    response_json = await extract_entries_data(response_xml.text)
    if need_datetime_sort:
        response_json = sorted(
            response_json,
            key=lambda x: datetime.fromisoformat(x["updated"]),
            reverse=True,
        )
    response_json = response_json[:num_results]

    for item in response_json:
        if need_publication_info:
            item["publication_info"] = await get_publication_info(
                item["title"], item["author"]
            )
        if need_pdf_link:
            item["pdf_link"] = await get_paper_pdf_link(item["cool_paper_id"])

    return response_json


@mcp.tool(
    name="get_publication_info", description="Get publication information for a paper"
)
async def get_publication_info(title: str, author: str = None) -> dict:
    ccf_rank_map = await load_ccf_ranking()
    query = title
    if author:
        query += f" author:{author}"
    api_url = f"https://dblp.org/search/publ/api"
    params = {
        "q": query,
        "format": "json",
    }
    headers = {"User-Agent": UserAgent().random}

    async with httpx.AsyncClient(proxy=proxies["http"] if proxies else None) as client:
        response = await client.get(api_url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()

    publication_info = {"venue": "arxiv", "ccf_rank": "None"}  # 默认无 CCF 评级
    if "result" not in data or "hits" not in data["result"]:
        return publication_info

    hits = data["result"]["hits"]
    if hits.get("@total", "0") == "0" or "hit" not in hits:
        return publication_info

    # 获取第一个匹配结果
    hit = hits["hit"][0]
    if "info" not in hit:
        return publication_info

    info = hit["info"]

    # 基本出版信息
    if "venue" in info:
        venue = info["venue"]
        publication_info["venue"] = venue

        # 查找 CCF 评级
        venue_lower = venue.lower()
        if venue_lower in ccf_rank_map:
            publication_info["ccf_rank"] = ccf_rank_map[venue_lower]

        # 如果在 info 中有更详细的会议/期刊信息，也尝试匹配 CCF 评级
        if "journal" in info:
            journal = info["journal"]
            journal_lower = journal.lower()
            if journal_lower in ccf_rank_map:
                publication_info["ccf_rank"] = ccf_rank_map[journal_lower]
                publication_info["journal"] = journal

        if "booktitle" in info:
            booktitle = info["booktitle"]
            booktitle_lower = booktitle.lower()
            if booktitle_lower in ccf_rank_map:
                publication_info["ccf_rank"] = ccf_rank_map[booktitle_lower]
                publication_info["booktitle"] = booktitle

    if "year" in info:
        publication_info["year"] = info["year"]

    return publication_info


def extract_pdf_link(html_content):
    patterns = [
        r'/pdf\?url=([^"\'&\s)]+)',  # 方法1: /pdf?url=
        r"togglePdf\([^,]+,\s*['\"]([^'\"]+)['\"]",  # 方法2: onclick参数
        r'https://arxiv\.org/pdf/[^"\'&\s)]+',  # 方法3: 直接ArXiv链接
        r'https://openreview\.net/pdf\?id=[^"\'&\s)]+',  # 方法4: 直接OpenReview链接
        r'https://[^"\'&\s)]+\.pdf(?:\?[^"\'&\s)]*)?',  # 方法5: 通用PDF链接
    ]

    for i, pattern in enumerate(patterns):
        match = re.search(pattern, html_content)
        if match:
            # 前两个模式需要取第一个捕获组，后面的取整个匹配
            return match.group(1) if i < 2 else match.group()

    return None


@mcp.tool(
    name="get_paper_pdf_link",
    description="Get of the paper, not the cool paper link!",
)
async def get_paper_pdf_link(cool_paper_id: str) -> str:
    api_url = cool_paper_id
    async with httpx.AsyncClient() as client:
        response = await client.get(api_url)
        response.raise_for_status()
        html_content = response.text
        pdf_link = extract_pdf_link(html_content)
        return pdf_link


def format_filename(title: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "_", title.strip())[:100] + ".pdf"


@mcp.tool(name="download_paper_pdf", description="Download paper pdf")
async def download_paper_pdf(title: str, pdf_link: str) -> str:
    async with httpx.AsyncClient() as client:
        response = await client.get(pdf_link)
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


@mcp.tool(name="list_downloaded_papers", description="When you need to read a paper, first List all paths of downloaded papers")
async def list_downloaded_papers() -> list[str]:
    return [file for file in Path("./data").iterdir() if file.suffix == ".pdf"]


@mcp.tool(name="extract_pdf_text", description="Extract text from a PDF file")
async def extract_pdf_text(pdf_path: str) -> str:

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
