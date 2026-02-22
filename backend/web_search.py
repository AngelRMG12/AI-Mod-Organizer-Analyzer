"""
Real-time web search for mod conflict reports.
Searches Reddit and Nexus Mods forums for posts related to the bug description.
Results are injected into the LLM prompt to give it fresh, specific context.
"""

import asyncio
import logging
from urllib.parse import quote_plus

import httpx

log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "AI-Mod-Conflict-Analyzer/0.1 (mod conflict research tool)",
    "Accept": "application/json",
}

SUBREDDITS = ["skyrimmods", "FalloutMods", "fo4mods", "Morrowind", "oblivionmods"]


async def search_reddit(query: str, limit: int = 5) -> list[dict]:
    """
    Searches Reddit via the public JSON API (no auth needed).
    Returns posts with title, text snippet, and URL.
    """
    results = []
    encoded = quote_plus(query)
    url = f"https://www.reddit.com/r/skyrimmods/search.json?q={encoded}&limit={limit}&sort=relevance&t=all"

    try:
        async with httpx.AsyncClient(headers=HEADERS, timeout=10, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                return results
            data = resp.json()
            for post in data.get("data", {}).get("children", []):
                pd = post.get("data", {})
                text = pd.get("selftext", "").strip()[:400]
                results.append({
                    "source": "Reddit r/skyrimmods",
                    "title": pd.get("title", ""),
                    "snippet": text if text else "(no body)",
                    "url": f"https://reddit.com{pd.get('permalink', '')}",
                    "score": pd.get("score", 0),
                })
        log.info(f"Reddit: {len(results)} results for '{query}'")
    except Exception as exc:
        log.warning(f"Reddit search failed: {exc}")

    return results


async def search_nexus_forum(query: str, limit: int = 5) -> list[dict]:
    """
    Searches Nexus Mods forum via their search page.
    Parses the HTML to extract post titles and snippets.
    """
    results = []
    encoded = quote_plus(query)
    url = f"https://forums.nexusmods.com/search/?q={encoded}&type=forums_topic&sortby=relevancy"

    try:
        async with httpx.AsyncClient(
            headers={**HEADERS, "Accept": "text/html"},
            timeout=10,
            follow_redirects=True,
        ) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                return results

            from html.parser import HTMLParser

            class NexusParser(HTMLParser):
                def __init__(self):
                    super().__init__()
                    self.results = []
                    self._in_title = False
                    self._in_snippet = False
                    self._current = {}

                def handle_starttag(self, tag, attrs):
                    attrs_dict = dict(attrs)
                    classes = attrs_dict.get("class", "")
                    if "ipsStreamItem_title" in classes:
                        self._in_title = True
                        self._current = {}
                    if "ipsStreamItem_snippet" in classes:
                        self._in_snippet = True
                    if tag == "a" and self._in_title and "href" in attrs_dict:
                        self._current["url"] = attrs_dict["href"]

                def handle_data(self, data):
                    data = data.strip()
                    if not data:
                        return
                    if self._in_title:
                        self._current["title"] = data
                    elif self._in_snippet:
                        self._current["snippet"] = data[:400]

                def handle_endtag(self, tag):
                    if self._in_title and tag in ("h2", "h3"):
                        self._in_title = False
                    if self._in_snippet and tag == "div":
                        self._in_snippet = False
                        if self._current.get("title"):
                            self._current["source"] = "Nexus Mods Forums"
                            self.results.append(dict(self._current))
                            self._current = {}

            parser = NexusParser()
            parser.feed(resp.text)
            results = parser.results[:limit]
        log.info(f"Nexus: {len(results)} results for '{query}'")
    except Exception as exc:
        log.warning(f"Nexus search failed: {exc}")

    return results


async def search_all(bug_description: str, mods: list[str]) -> list[dict]:
    """
    Runs Reddit and Nexus searches in parallel.
    Builds a smart query combining the bug description with mod names.
    """
    # Build focused search query
    top_mods = " ".join(mods[:3]) if mods else ""
    query = f"{bug_description} skyrim mod {top_mods}".strip()

    reddit_task = search_reddit(query)
    nexus_task = search_nexus_forum(query)

    reddit_results, nexus_results = await asyncio.gather(reddit_task, nexus_task)
    all_results = reddit_results + nexus_results

    # Sort by source reliability and score
    all_results.sort(key=lambda x: x.get("score", 0), reverse=True)
    return all_results[:8]


def format_search_results_for_prompt(results: list[dict]) -> str:
    """Formats search results into a compact block to inject into the LLM prompt."""
    if not results:
        return ""

    lines = ["\n\n--- REAL-TIME WEB SEARCH RESULTS (use this context) ---"]
    for i, r in enumerate(results, 1):
        lines.append(
            f"\n[{i}] {r['source']}: {r.get('title', 'No title')}\n"
            f"    {r.get('snippet', '')[:300]}\n"
            f"    URL: {r.get('url', '')}"
        )
    lines.append("\n--- END SEARCH RESULTS ---")
    return "\n".join(lines)
