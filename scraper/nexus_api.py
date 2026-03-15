"""
Búsqueda en Nexus Mods vía API GraphQL.
Evita 403 del scraping del foro. Sin API key: prueba sin auth.
Con NEXUS_API_KEY en .env: mejor rate limit.
"""

import logging
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

# Cargar .env
for p in [
    Path(__file__).resolve().parent.parent / ".env",
    Path.cwd() / ".env",
]:
    if p.exists():
        load_dotenv(p)
        break

log = logging.getLogger(__name__)

NEXUS_GRAPHQL = "https://api.nexusmods.com/v2/graphql"
GAME_DOMAIN = "skyrimspecialedition"


def _get_headers() -> dict:
    key = os.environ.get("NEXUS_API_KEY", "").strip()
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "AI-Mod-Conflict-Analyzer/0.3 (educational modding tool)",
        "Accept": "application/json",
    }
    if key:
        headers["apikey"] = key
    return headers


def _keyword_variants(keyword: str) -> list[str]:
    """Genera variantes para aumentar resultados (MATCHES exige todos los términos)."""
    words = [w for w in keyword.split() if len(w) >= 2][:5]
    skip = {"bug", "fix", "glitch", "error", "problem", "help", "the", "and"}
    words = [w for w in words if w.lower() not in skip]
    variants = []
    if len(words) >= 2:
        variants.append(" ".join(words[:2]))  # primeras 2 palabras
    if len(words) >= 3:
        variants.append(" ".join(words[:3]))
    if words:
        variants.append(words[0])  # término más específico solo
    if not variants:
        variants.append("skyrim")
    return list(dict.fromkeys(variants))[:4]  # sin duplicados, máx 4 variantes


def search_nexus_mods(keyword: str, limit: int = 8) -> list[dict]:
    """
    Busca mods en Skyrim SE usando la API GraphQL de Nexus.
    Prueba varias variantes del keyword (MATCHES exige todos los términos).
    """
    query = """
    query searchMods($filter: ModsFilter, $count: Int, $offset: Int) {
      mods(filter: $filter, count: $count, offset: $offset) {
        nodes {
          modId
          name
          summary
        }
        totalCount
      }
    }
    """
    seen_ids = set()
    results = []
    per_variant = max(3, limit // 2)

    for variant in _keyword_variants(keyword):
        if len(results) >= limit:
            break
        variables = {
            "filter": {
                "op": "AND",
                "gameDomainName": [{"value": GAME_DOMAIN, "op": "EQUALS"}],
                "nameStemmed": [{"value": variant, "op": "MATCHES"}],
            },
            "count": per_variant,
            "offset": 0,
        }
        try:
            with httpx.Client(timeout=15) as client:
                resp = client.post(
                    NEXUS_GRAPHQL,
                    json={"query": query, "variables": variables},
                    headers=_get_headers(),
                )
            if resp.status_code != 200:
                continue
            data = resp.json()
            if data.get("errors"):
                continue
            mods_data = data.get("data", {}).get("mods") or {}
            nodes = mods_data.get("nodes") or []
            for m in nodes:
                mod_id = m.get("modId")
                if mod_id in seen_ids:
                    continue
                seen_ids.add(mod_id)
                name = m.get("name", "")
                summary = (m.get("summary") or "")[:350]
                url = f"https://www.nexusmods.com/{GAME_DOMAIN}/mods/{mod_id}" if mod_id else ""
                results.append({
                    "source": "Nexus Mods",
                    "title": name,
                    "snippet": summary or "(mod sin descripción)",
                    "url": url,
                    "score": 0,
                })
        except Exception as e:
            log.debug(f"Nexus API variant '{variant}': {e}")
            continue

    if results:
        log.info(f"Nexus API: {len(results)} mods para '{keyword[:40]}'")
    return results[:limit]
