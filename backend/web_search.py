"""
Búsqueda web: queries generadas por LLM, scraper + Reddit fallback.
"""

import asyncio
import logging
import sys
from pathlib import Path

from .local_investigator import search_reddit_fallback, filter_relevant_results

root = Path(__file__).resolve().parent.parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

log = logging.getLogger(__name__)


async def search_with_queries(
    search_queries: list[str],
    bug_description: str,
    filter_words: list[str] | None = None,
) -> list[dict]:
    """
    Busca con las queries que generó el LLM. Filtra por palabras del bug.
    """
    raw_results = []
    seen_urls = set()

    # 1. Scraper: búsqueda profunda (más queries, más resultados)
    if search_queries:
        try:
            from scraper.scraper import ConflictScraper
            scraper = ConflictScraper()
            raw_results = await asyncio.to_thread(
                scraper.search_with_queries,
                search_queries,
                limit_per_query=8,
            )
            seen_urls = {r.get("url") for r in raw_results if r.get("url")}
            log.info(f"Scraper: {len(raw_results)} results")
        except Exception as exc:
            log.warning(f"Scraper failed: {exc}")

    # 2. Reddit directo: TODAS las queries para búsqueda profunda
    for q in search_queries[:10]:
        fb = await search_reddit_fallback(q, limit=10)
        for r in fb:
            if r.get("url") and r["url"] not in seen_urls:
                raw_results.append(r)
                seen_urls.add(r["url"])

    raw_results.sort(key=lambda x: x.get("score", 0), reverse=True)

    # 3. Filtrar: solo resultados que mencionan palabras del bug
    if filter_words:
        results = filter_relevant_results(raw_results, filter_words)
    else:
        results = raw_results[:15]

    return results[:15]


def format_search_results_for_prompt(results: list[dict]) -> str:
    """Formats search results for the LLM prompt."""
    if not results:
        return ""

    lines = ["\n\n--- WEB SEARCH RESULTS (Reddit/Nexus - use these sources) ---"]
    for i, r in enumerate(results, 1):
        url = r.get("url", "")
        if not url:
            continue
        lines.append(
            f"\n[{i}] {r.get('source','')}: {r.get('title', 'No title')}\n"
            f"    {r.get('snippet', '')[:300]}\n"
            f"    URL: {url}"
        )
    lines.append("\n--- END WEB SEARCH ---")
    return "\n".join(lines)
