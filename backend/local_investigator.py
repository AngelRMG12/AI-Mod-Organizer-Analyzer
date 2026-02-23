"""
Investigador local: analiza archivos y conflictos. Solo datos, cero mapeos hardcodeados.
Las búsquedas las genera el LLM (search_planner).
"""

import logging

import httpx
from urllib.parse import quote_plus

log = logging.getLogger(__name__)


def investigate(
    bug_description: str,
    file_conflicts: list[dict],
    overwrite_files: list[str],
    mods: list[str],
) -> dict:
    """
    Análisis de archivos: conflictos y overwrite.
    Devuelve brief y priority_mods. No genera search_queries (eso lo hace el LLM).
    """
    brief_lines = []
    priority_mods = set()

    # 1. Mods en conflictos reales (siempre relevantes)
    for c in file_conflicts[:30]:
        for m in c.get("mods", []):
            priority_mods.add(m)
        if len(brief_lines) < 3:
            brief_lines.append(f"{c['file']}: {' vs '.join(c['mods'][:3])}")

    # 2. Mods cuyo nombre comparte palabras con el bug (dinámico)
    bug_words = {w.lower() for w in bug_description.split() if len(w) >= 3}
    for mod in mods:
        mod_lower = mod.lower()
        for w in bug_words:
            if w in mod_lower:
                priority_mods.add(mod)
                break

    # 3. Overwrite
    if overwrite_files:
        brief_lines.append(f"Overwrite: {len(overwrite_files)} archivos")

    brief = " | ".join(brief_lines[:5]) if brief_lines else "Sin conflictos detectados."

    return {
        "brief": brief,
        "priority_mods": list(priority_mods)[:20],
    }


def filter_relevant_results(
    results: list[dict],
    filter_words: list[str],
) -> list[dict]:
    """
    Descarta resultados cuyo título/snippet no mencionan las palabras del bug.
    Si todo se filtra, devuelve los 5 mejores por score (mejor algo que nada).
    """
    if not results:
        return []
    if not filter_words:
        return results[:10]

    filtered = [r for r in results if _matches_filter(r, filter_words)]
    if not filtered and results:
        log.info("Filter too strict, returning top 5 by score")
        return results[:5]
    log.info(f"Filter: {len(results)} → {len(filtered)}")
    return filtered[:10]


def _matches_filter(r: dict, words: list[str]) -> bool:
    text = (r.get("title", "") + " " + r.get("snippet", "")).lower()
    return any(w in text for w in words)


async def search_reddit_fallback(query: str, limit: int = 8) -> list[dict]:
    """Búsqueda directa Reddit con httpx."""
    results = []
    try:
        q = quote_plus(query)
        url = f"https://www.reddit.com/r/skyrimmods/search.json?q={q}&restrict_sr=1&limit={limit}&sort=relevance"
        async with httpx.AsyncClient(
            headers={"User-Agent": "AI-Mod-Conflict-Analyzer/1.0"},
            timeout=15,
        ) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                return results
            data = resp.json()
            for post in data.get("data", {}).get("children", []):
                pd = post.get("data", {})
                results.append({
                    "source": "Reddit r/skyrimmods",
                    "title": pd.get("title", ""),
                    "snippet": (pd.get("selftext", "") or "")[:300] or "(no body)",
                    "url": f"https://reddit.com{pd.get('permalink', '')}",
                    "score": pd.get("score", 0),
                })
        log.info(f"Reddit: {len(results)} for '{query[:40]}'")
    except Exception as exc:
        log.warning(f"Reddit failed: {exc}")
    return results
