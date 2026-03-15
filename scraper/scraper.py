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
from urllib.parse import quote_plus

import httpx

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

KB_PATH = Path(__file__).parent.parent / "knowledge_base" / "conflicts.json"

# Keywords to search for bug reports (multilingual)
SEARCH_KEYWORDS = [
    # English — specific bugs
    "skyrim black face bug fix mod organizer",
    "skyrim t-pose animation fix FNIS nemesis",
    "skyrim CTD crash on load mod conflict",
    "papyrus log error script mod conflict",
    "skyrim missing textures purple mesh fix",
    "skyrim infinite loading screen mod fix",
    "skyrim NPC invisible missing head fix",
    "skyrim freezing stuttering mod conflict",
    "skyrim SkyUI interface not loading fix",
    "SKSE plugin failed to load skyrim",
    "skyrim mod load order conflict LOOT fix",
    "skyrim overwrite conflict mod organizer fix",
    "skyrim facegen data missing NPC overhaul",
    "skyrim animation not playing XP32 skeleton fix",
    "RaceMenu crash CTD skyrim fix",
    # Spanish — bugs específicos
    "skyrim cara negra npc arreglo mod organizer",
    "skyrim t-pose animaciones arreglo FNIS",
    "skyrim crash carga conflicto mods solución",
    "skyrim texturas moradas arreglo",
    "skyrim pantalla de carga infinita mods",
    "error papyrus skyrim conflicto mods",
    # French
    "skyrim visage noir npc correction mod",
    "skyrim t-pose animation correction FNIS",
    "skyrim crash chargement conflit mods",
    # German
    "skyrim schwarzes gesicht npc mod konflikt lösung",
    "skyrim t-pose animation fehler beheben",
    "skyrim absturz ladebildschirm mod konflikt",
    # Portuguese
    "skyrim rosto preto npc correção mod",
    "skyrim crash carregamento conflito mods solução",
    # Fallout 4
    "fallout 4 mod conflict crash fix",
    "fallout 4 missing textures mod organizer",
    "fallout 4 CTD load order conflict fix",
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


# Nexus forum: suele bloquear scrapers (403). Intentamos headers de navegador.
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://forums.nexusmods.com/",
}


def _search_nexus_mods(keyword: str, limit: int = 5) -> list[dict]:
    """Busca mods vía API Nexus (sin 403). Fallback si falla."""
    try:
        from scraper.nexus_api import search_nexus_mods
        return search_nexus_mods(keyword, limit=limit)
    except Exception as exc:
        log.debug(f"Nexus API: {exc}")
        return []


class ConflictScraper:
    def __init__(self, llm_url: str = "http://localhost:11434", llm_model: str = "llama3"):
        self.llm_url = llm_url
        self.llm_model = llm_model
        self.session = httpx.Client(
            headers={"User-Agent": "AI-Mod-Conflict-Analyzer/0.2"},
            timeout=30,
            follow_redirects=True,
        )
        self._nexus_blocked = False  # Para no spamear log cuando 403

    def scrape_reddit(self, keyword: str, limit: int = 10) -> list[dict]:
        """Fetches Reddit posts via the JSON API (no auth needed)."""
        q = quote_plus(keyword)
        url = f"https://www.reddit.com/r/skyrimmods/search.json?q={q}&restrict_sr=1&limit={limit}&sort=relevance"
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

    def _build_search_keyword(self, bug: str) -> str:
        """
        Construye keyword para búsqueda. r/skyrimmods es mayormente inglés,
        así que añadimos términos en inglés cuando el bug está en español.
        """
        b = bug.lower().strip()[:80]
        # Ayuda mínima: términos comunes EN para que Reddit devuelva resultados
        if any(t in b for t in ["ojo", "ojos", "brill", "destell"]):
            return "skyrim eyes shiny bright fix"
        if any(t in b for t in ["cara negra", "black face"]):
            return "skyrim black face bug fix"
        if any(t in b for t in ["t-pose", "tpose"]):
            return "skyrim t-pose animation fix"
        if any(t in b for t in ["crash", "ctd"]):
            return "skyrim crash CTD fix"
        # Por defecto: skyrim + lo que escribió el usuario
        return "skyrim " + b

    def search_for_bug(self, bug_description: str, limit: int = 10) -> list[dict]:
        """
        Busca en Reddit y Nexus. Devuelve formato compatible con el analyzer.
        """
        keyword = self._build_search_keyword(bug_description)
        reddit, nexus = [], []
        try:
            reddit = self.scrape_reddit(keyword, limit=limit)
            # Para ojos: segunda búsqueda para ampliar resultados
            if "eyes" in keyword and len(reddit) < 4:
                extra = self.scrape_reddit("skyrim eyes too bright ENB", limit=5)
                seen = {p.get("url") for p in reddit}
                for p in extra:
                    if p.get("url") and p["url"] not in seen:
                        reddit.append(p)
                        seen.add(p["url"])
        except Exception as e:
            log.warning(f"Reddit search failed: {e}")
        try:
            nexus = self.scrape_nexus_forum(keyword)
        except Exception as e:
            log.warning(f"Nexus search failed: {e}")

        results = []
        for p in reddit:
            results.append({
                "source": "Reddit r/skyrimmods",
                "title": p.get("title", ""),
                "snippet": (p.get("text") or "")[:400] or "(no body)",
                "url": p.get("url", ""),
                "score": p.get("score", 0),
            })
        for p in nexus[:limit]:
            results.append({
                "source": "Nexus Mods Forums",
                "title": p.get("title", ""),
                "snippet": (p.get("text") or "")[:400],
                "url": p.get("url", ""),
                "score": 0,
            })

        results.sort(key=lambda x: x.get("score", 0), reverse=True)
        return results[:8]

    def search_with_queries(self, queries: list[str], limit_per_query: int = 5) -> list[dict]:
        """
        Búsqueda profunda: Reddit + Nexus (API primero, forum como fallback).
        """
        seen_urls = set()
        all_results = []
        for q in queries[:12]:
            reddit, nexus = [], []
            try:
                reddit = self.scrape_reddit(q, limit=limit_per_query)
            except Exception as e:
                log.warning(f"Reddit failed for '{q[:40]}': {e}")
            # Nexus: API primero (no da 403), luego forum si falla
            nexus = _search_nexus_mods(q, limit=limit_per_query)
            if not nexus:
                try:
                    nexus = self.scrape_nexus_forum(q)
                except Exception:
                    pass
            for p in reddit:
                r = {
                    "source": "Reddit r/skyrimmods",
                    "title": p.get("title", ""),
                    "snippet": (p.get("text") or "")[:400] or "(no body)",
                    "url": p.get("url", ""),
                    "score": p.get("score", 0),
                }
                if r["url"] and r["url"] not in seen_urls:
                    seen_urls.add(r["url"])
                    all_results.append(r)
            for p in nexus[:limit_per_query]:
                href = p.get("url", "")
                if href and not href.startswith("http"):
                    href = "https://forums.nexusmods.com" + (href if href.startswith("/") else "/" + href)
                r = {
                    "source": "Nexus Mods Forums",
                    "title": p.get("title", ""),
                    "snippet": (p.get("text") or "")[:400],
                    "url": href,
                    "score": 0,
                }
                if r["url"] and r["url"] not in seen_urls:
                    seen_urls.add(r["url"])
                    all_results.append(r)
        all_results.sort(key=lambda x: x.get("score", 0), reverse=True)
        return all_results[:20]

    def scrape_nexus_forum(self, keyword: str) -> list[dict]:
        """Searches Nexus Mods forum. Nexus suele bloquear scrapers (403)."""
        if not HAS_BS4:
            return []
        if self._nexus_blocked:
            return []
        q = quote_plus(keyword)
        url = f"https://forums.nexusmods.com/search/?q={q}&type=forums_topic"
        posts = []
        try:
            resp = self.session.get(url, headers=BROWSER_HEADERS)
            if resp.status_code == 403:
                self._nexus_blocked = True
                log.info("Nexus bloquea scrapers (403). Usando solo Reddit.")
                return []
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            for result in soup.select("li.ipsStreamItem")[:10]:
                title_el = result.select_one("h2 a")
                snippet_el = result.select_one("div.ipsStreamItem_snippet")
                if title_el:
                    href = title_el.get("href", "")
                    if href and not href.startswith("http"):
                        href = "https://forums.nexusmods.com" + (href if href.startswith("/") else "/" + href)
                    posts.append({
                        "title": title_el.get_text(strip=True),
                        "text": snippet_el.get_text(strip=True) if snippet_el else "",
                        "url": href or "",
                    })
            log.info(f"Nexus: found {len(posts)} for '{keyword[:40]}'")
        except Exception as exc:
            if "403" in str(exc):
                self._nexus_blocked = True
                log.info("Nexus bloquea scrapers (403). Usando solo Reddit.")
            else:
                log.debug(f"Nexus: {exc}")
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
