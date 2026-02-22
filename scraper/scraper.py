"""
Conflict Knowledge Scraper
Crawls Nexus Mods posts, Reddit, and GitHub issues to find known
mod conflict reports in multiple languages, then uses an LLM to
classify and normalize them into the knowledge base format.

Inspired by sammwyy/inkshelf scraper approach:
  - Automated browsing to find content by keywords
  - AI classification of raw text
  - Structured output saved to knowledge_base/conflicts.json
"""

import os
import json
import time
import logging
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict

import httpx
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

KB_PATH = Path(__file__).parent.parent / "knowledge_base" / "conflicts.json"

# Keywords to search for bug reports (multilingual)
SEARCH_KEYWORDS = [
    # English
    "skyrim mod conflict", "mod bug fix", "black face bug skyrim",
    "t-pose skyrim mod", "CTD mod conflict", "papyrus log error mod",
    # Spanish
    "conflicto mods skyrim", "bug mods skyrim solución",
    # French
    "conflit mods skyrim", "bug mods skyrim correction",
    # German
    "mod konflikt skyrim", "skyrim mod fehler",
    # Portuguese
    "conflito mods skyrim", "bug mods skyrim solução",
]

SOURCES = [
    "reddit.com/r/skyrimmods",
    "reddit.com/r/FalloutMods",
    "nexusmods.com",
    "github.com",
]


@dataclass
class ConflictEntry:
    bug_keyword: str
    mods: list[str]
    confidence: float
    fix: str
    source_url: str
    language: str = "en"


class ConflictScraper:
    def __init__(self, llm_url: str = "http://localhost:11434", llm_model: str = "llama3"):
        self.llm_url = llm_url
        self.llm_model = llm_model
        self.session = httpx.Client(
            headers={"User-Agent": "AI-Mod-Conflict-Analyzer/0.1 (educational)"},
            timeout=30,
            follow_redirects=True,
        )

    def scrape_reddit(self, keyword: str, limit: int = 10) -> list[dict]:
        """Fetches Reddit posts via the JSON API (no auth needed)."""
        url = f"https://www.reddit.com/r/skyrimmods/search.json?q={keyword}&limit={limit}&sort=relevance"
        posts = []
        try:
            resp = self.session.get(url)
            resp.raise_for_status()
            data = resp.json()
            for post in data.get("data", {}).get("children", []):
                pd = post["data"]
                posts.append({
                    "title": pd.get("title", ""),
                    "text": pd.get("selftext", ""),
                    "url": f"https://reddit.com{pd.get('permalink', '')}",
                    "score": pd.get("score", 0),
                })
            log.info(f"Reddit: found {len(posts)} posts for '{keyword}'")
        except Exception as exc:
            log.warning(f"Reddit scrape failed for '{keyword}': {exc}")
        return posts

    def scrape_nexus_forum(self, keyword: str) -> list[dict]:
        """Searches Nexus Mods forum via their search endpoint."""
        url = f"https://forums.nexusmods.com/search/?q={keyword}&type=forums_topic"
        posts = []
        try:
            resp = self.session.get(url)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            for result in soup.select("li.ipsStreamItem")[:10]:
                title_el = result.select_one("h2 a")
                snippet_el = result.select_one("div.ipsStreamItem_snippet")
                if title_el:
                    posts.append({
                        "title": title_el.get_text(strip=True),
                        "text": snippet_el.get_text(strip=True) if snippet_el else "",
                        "url": title_el.get("href", ""),
                    })
            log.info(f"Nexus: found {len(posts)} results for '{keyword}'")
        except Exception as exc:
            log.warning(f"Nexus scrape failed for '{keyword}': {exc}")
        return posts

    def classify_with_llm(self, post: dict) -> Optional[ConflictEntry]:
        """
        Sends a raw post to the local LLM and asks it to extract
        structured conflict information.
        """
        prompt = f"""You are a mod conflict classifier. Given this post, extract conflict info.

Title: {post['title']}
Text: {post['text'][:800]}
URL: {post.get('url', '')}

Return ONLY valid JSON in this format (or null if not a conflict report):
{{
  "bug_keyword": "short bug name (e.g. 'black face bug')",
  "mods": ["ModName1", "ModName2"],
  "confidence": 0.8,
  "fix": "brief fix description",
  "language": "en"
}}"""

        try:
            resp = self.session.post(
                f"{self.llm_url}/api/generate",
                json={"model": self.llm_model, "prompt": prompt, "stream": False},
                timeout=60,
            )
            resp.raise_for_status()
            content = resp.json().get("response", "").strip()
            # Extract JSON from response
            import re
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if match:
                data = json.loads(match.group())
                if data and data.get("bug_keyword") and data.get("mods"):
                    return ConflictEntry(
                        bug_keyword=data["bug_keyword"].lower(),
                        mods=data["mods"],
                        confidence=float(data.get("confidence", 0.6)),
                        fix=data.get("fix", ""),
                        source_url=post.get("url", ""),
                        language=data.get("language", "en"),
                    )
        except Exception as exc:
            log.warning(f"LLM classification failed: {exc}")
        return None

    def run(self, keywords: Optional[list[str]] = None, delay: float = 1.5):
        """Main scrape loop. Crawls sources, classifies posts, saves to KB."""
        keywords = keywords or SEARCH_KEYWORDS
        existing_kb = self._load_kb()
        new_entries = 0

        for keyword in keywords:
            log.info(f"Processing keyword: '{keyword}'")
            posts = self.scrape_reddit(keyword)
            time.sleep(delay)

            for post in posts:
                if not post["title"] and not post["text"]:
                    continue
                entry = self.classify_with_llm(post)
                if entry:
                    key = entry.bug_keyword
                    if key not in existing_kb:
                        existing_kb[key] = {
                            "mods": entry.mods,
                            "confidence": entry.confidence,
                            "fix": entry.fix,
                            "sources": [entry.source_url],
                            "language": entry.language,
                        }
                        new_entries += 1
                    else:
                        # Merge mods
                        for mod in entry.mods:
                            if mod not in existing_kb[key]["mods"]:
                                existing_kb[key]["mods"].append(mod)
                        if entry.source_url not in existing_kb[key].get("sources", []):
                            existing_kb[key].setdefault("sources", []).append(entry.source_url)
                time.sleep(delay)

        self._save_kb(existing_kb)
        log.info(f"Scrape complete. Added {new_entries} new conflict entries.")

    def _load_kb(self) -> dict:
        if KB_PATH.exists():
            with open(KB_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_kb(self, kb: dict):
        KB_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(KB_PATH, "w", encoding="utf-8") as f:
            json.dump(kb, f, indent=2, ensure_ascii=False)
        log.info(f"Knowledge base saved to {KB_PATH}")


if __name__ == "__main__":
    scraper = ConflictScraper()
    scraper.run()
