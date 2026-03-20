#!/usr/bin/env python3
"""
WebSearchAgent — Tavily-backed web search for the study pipeline.

Applies source quality tier filtering and enriches top results via web_fetch.py.

Usage:
  python web_search_agent.py --query "explain the Krebs cycle"
  python web_search_agent.py --query "..." --max-results 8 --search-depth advanced
  python web_search_agent.py --query "..." --topic academic

Output:
  {
    "web_findings": [
      {
        "url": "...",
        "title": "...",
        "content": "...",
        "score": 0.95,
        "quality_tier": 1,
        "quality_label": "Gold",
        "publish_date": "...",
        "domain": "khanacademy.org"
      }
    ],
    "total_found": N,
    "filtered_count": N,
    "query": "..."
  }

Quality tiers:
  Tier 1 Gold:   Academic publishers, government/edu institutions, peer-reviewed sources,
                 trusted learning platforms (Khan Academy, Brilliant, Wolfram)
  Tier 2 Silver: Quality educational sites, reputable reference works, open courseware
  Tier 3 Bronze: Wikipedia, encyclopaedias, study guides, reputable news
  Tier 4 Skip:   SEO blogs, AI-generated content farms, low-quality tutorial mills
"""

import sys
import os
import json
import argparse
import subprocess
import re
from pathlib import Path
from typing import Optional

from paths import PYTHON_EXE
TOOLS_DIR  = Path(__file__).parent

# ---------------------------------------------------------------------------
# Source quality tier definitions (Constitution §IV)
# ---------------------------------------------------------------------------

TIER1_GOLD = [
    # Academic institutions & government
    r"\.gov$", r"\.edu$", r"\.ac\.uk$",
    r"arxiv\.org", r"pubmed\.ncbi\.nlm\.nih\.gov", r"ncbi\.nlm\.nih\.gov",
    r"ieee\.org", r"ieeexplore\.ieee\.org",
    r"acm\.org", r"dl\.acm\.org",
    r"nature\.com", r"science\.org",
    r"scholar\.google\.com", r"semanticscholar\.org",
    r"jstor\.org", r"springerlink\.com", r"link\.springer\.com",
    r"iso\.org", r"nist\.gov", r"who\.int", r"nih\.gov",
    r"plato\.stanford\.edu",
    # Trusted learning platforms
    r"khanacademy\.org",
    r"brilliant\.org",
    r"mathworld\.wolfram\.com",
    r"wolframalpha\.com",
    r"ocw\.mit\.edu",
    r"oyc\.yale\.edu",
    # India — government / official academic
    r"nptel\.ac\.in",
    r"ncert\.nic\.in",
    r"nios\.ac\.in",
    r"ugc\.ac\.in",
    r"shodhganga\.inflibnet\.ac\.in",
    r"ias\.ac\.in",
]

TIER2_SILVER = [
    # India — quality educational platforms
    r"byjus\.com",
    r"unacademy\.com",
    r"vedantu\.com",
    r"doubtnut\.com",
    # Open courseware & quality educational platforms
    r"coursera\.org(?!/articles)",  # courses yes, SEO articles no
    r"edx\.org",
    r"udacity\.com",
    r"openlearn\.open\.ac\.uk",
    r"saylor\.org",
    # Reference & encyclopaedias
    r"britannica\.com",
    r"mathshistory\.st-andrews\.ac\.uk",
    # Quality docs & developer references
    r"docs\.[a-z]+\.(com|io|org)",
    r"[a-z]+\.readthedocs\.io",
    r"developer\.mozilla\.org",     # MDN Web Docs
    r"github\.com/[^/]+/[^/]+$",   # repo homepages only
    r"pytorch\.org", r"tensorflow\.org",
    r"microsoft\.com/en-us/research",
    r"research\.google\.com", r"openai\.com/research",
]

TIER3_BRONZE = [
    # India — reference & exam prep
    r"shaalaa\.com",
    r"meritnation\.com",
    r"indiabix\.com",
    r"examrace\.com",
    r"jagranjosh\.com",
    # Encyclopaedias & reference
    r"en\.wikipedia\.org",
    # Study guides
    r"sparknotes\.com",
    r"cliffsnotes\.com",
    r"studysmarter\.(co\.uk|com)",
    r"thoughtco\.com",
    r"gradesaver\.com",
    # Educational media
    r"bbc\.(co\.uk|com)",           # covers BBC Bitesize (bbc.co.uk/bitesize)
    r"nationalgeographic\.com",
    r"smithsonianmag\.com",
    # Reputable news
    r"reuters\.com", r"apnews\.com",
    r"theregister\.com", r"arstechnica\.com",
    # CS reference (useful for programming students)
    r"geeksforgeeks\.org",
    r"developer\.mozilla\.org",     # MDN Web Docs
]

TIER4_SKIP = [
    r"medium\.com", r"substack\.com", r"hashnode\.dev",
    r"dev\.to", r"towardsdatascience\.com", r"analyticsvidhya\.com",
    r"w3schools\.com", r"javatpoint\.com",
    r"tutorialspoint\.com", r"simplilearn\.com",
    r"coursera\.org/articles",      # SEO article farm, not actual courses
]


def get_domain(url: str) -> str:
    m = re.search(r"https?://([^/]+)", url)
    return m.group(1).lower() if m else url.lower()


def score_quality(url: str) -> tuple[int, str]:
    """Return (tier, label) for a URL. Lower tier = higher quality."""
    domain = get_domain(url)
    # TIER4 is checked against the full URL so path-based rules (e.g. coursera.org/articles) work
    for pattern in TIER4_SKIP:
        if re.search(pattern, url.lower()):
            return 4, "Skip"
    for pattern in TIER1_GOLD:
        if re.search(pattern, domain):
            return 1, "Gold"
    for pattern in TIER2_SILVER:
        if re.search(pattern, domain):
            return 2, "Silver"
    for pattern in TIER3_BRONZE:
        if re.search(pattern, domain):
            return 3, "Bronze"
    return 3, "Bronze"  # default: treat unknown as bronze


# ---------------------------------------------------------------------------
# Tavily search
# ---------------------------------------------------------------------------

def tavily_search(query: str, max_results: int = 10, search_depth: str = "advanced",
                  topic: str = "general") -> list:
    """Call Tavily API and return raw results list."""
    try:
        from tavily import TavilyClient
    except ImportError:
        return [{"error": "tavily-python not installed. Run: pip install tavily-python"}]

    api_key = os.environ.get("TAVILY_API_KEY", "")
    if not api_key:
        # Fallback: read from Windows user-level environment (not always inherited by subprocesses)
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment") as key:
                api_key, _ = winreg.QueryValueEx(key, "TAVILY_API_KEY")
        except Exception:
            pass
    if not api_key:
        return [{"error": "TAVILY_API_KEY environment variable not set"}]

    try:
        client = TavilyClient(api_key=api_key)
        response = client.search(
            query=query,
            search_depth=search_depth,
            max_results=max_results,
            topic=topic,
            include_answer=False,
            include_raw_content=False,
        )
        return response.get("results", [])
    except Exception as e:
        return [{"error": str(e)}]


# ---------------------------------------------------------------------------
# web_fetch enrichment
# ---------------------------------------------------------------------------

def enrich_with_web_fetch(url: str) -> dict:
    """Call web_fetch.py to get publish_date and richer metadata."""
    try:
        result = subprocess.run(
            [PYTHON_EXE, str(TOOLS_DIR / "web_fetch.py"), url],
            capture_output=True, text=True, encoding="utf-8", timeout=20
        )
        data = json.loads(result.stdout)
        return {
            "publish_date": data.get("publish_date"),
            "description":  data.get("description", ""),
        }
    except Exception:
        return {"publish_date": None, "description": ""}


# ---------------------------------------------------------------------------
# Main search pipeline
# ---------------------------------------------------------------------------

def search(query: str, max_results: int = 10, search_depth: str = "advanced",
           topic: str = "general", skip_tier4: bool = True,
           enrich_top_n: int = 5) -> dict:
    """
    Full pipeline: Tavily search → quality tier filter → web_fetch enrichment.
    Returns structured web_findings list.
    """
    raw_results = tavily_search(query, max_results=max_results,
                                search_depth=search_depth, topic=topic)

    # Surface API errors immediately
    if raw_results and "error" in raw_results[0]:
        return {
            "web_findings": [],
            "total_found": 0,
            "filtered_count": 0,
            "query": query,
            "error": raw_results[0]["error"],
        }

    findings = []
    skipped = 0

    for r in raw_results:
        url = r.get("url", "")
        tier, label = score_quality(url)

        if skip_tier4 and tier == 4:
            skipped += 1
            continue

        findings.append({
            "url":           url,
            "title":         r.get("title", ""),
            "content":       r.get("content", ""),   # Tavily snippet
            "score":         round(r.get("score", 0.0), 4),
            "quality_tier":  tier,
            "quality_label": label,
            "publish_date":  None,
            "description":   "",
            "domain":        get_domain(url),
        })

    # Sort: tier ASC (Gold first), then Tavily score DESC
    findings.sort(key=lambda x: (x["quality_tier"], -x["score"]))

    # Enrich top N with web_fetch for publish_date + description
    for i, f in enumerate(findings[:enrich_top_n]):
        enriched = enrich_with_web_fetch(f["url"])
        findings[i]["publish_date"] = enriched["publish_date"]
        findings[i]["description"]  = enriched["description"] or f["content"][:200]

    return {
        "web_findings":   findings,
        "total_found":    len(raw_results),
        "filtered_count": skipped,
        "query":          query,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="WebSearchAgent — Tavily-backed web search with quality tier filtering"
    )
    parser.add_argument("--query",        required=True, help="Search query")
    parser.add_argument("--max-results",  type=int, default=10,
                        help="Max results from Tavily (default: 10)")
    parser.add_argument("--search-depth", default="advanced",
                        choices=["basic", "advanced"],
                        help="Tavily search depth (default: advanced)")
    parser.add_argument("--topic",        default="general",
                        choices=["general", "news"],
                        help="Tavily topic filter (default: general)")
    parser.add_argument("--enrich-top",   type=int, default=5,
                        help="Enrich top N results via web_fetch (default: 5)")
    parser.add_argument("--include-tier4", action="store_true",
                        help="Include Tier 4 (low-quality) results")
    args = parser.parse_args()

    result = search(
        query=args.query,
        max_results=args.max_results,
        search_depth=args.search_depth,
        topic=args.topic,
        skip_tier4=not args.include_tier4,
        enrich_top_n=args.enrich_top,
    )

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
