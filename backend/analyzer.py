"""
Core analysis logic: combines local heuristics + real-time web search + LLM.

Flow:
  1. Local heuristic pass   → fast, offline, always runs
  2. Real-time web search   → Reddit + Nexus, runs in parallel
  3. LLM call               → gets web results as context in the prompt
  4. Parse + merge results  → deduplicated, sorted by confidence
"""

import json
import logging
from .llm import call_llm
from .knowledge import load_knowledge_base, local_heuristic_search
from .web_search import search_all, format_search_results_for_prompt

log = logging.getLogger(__name__)
KB = load_knowledge_base()


async def run_analysis(
    mods: list[str],
    plugins: list[str],
    bug_description: str,
    game: str = "Skyrim SE",
) -> dict:
    # 1. Local heuristic pass (fast, offline, always runs)
    local_hits = local_heuristic_search(mods, bug_description, KB)

    # 2. Real-time web search (Reddit + Nexus in parallel)
    web_results = []
    try:
        web_results = await search_all(bug_description, mods)
        log.info(f"Web search returned {len(web_results)} results")
    except Exception as exc:
        log.warning(f"Web search failed (continuing without): {exc}")

    # 3. Build LLM prompt with web context injected
    prompt = _build_prompt(mods, plugins, bug_description, game, local_hits, web_results)

    # 4. Call LLM — graceful fallback if unavailable
    llm_response = {"content": "", "tokens_used": None, "error": None}
    try:
        llm_response = await call_llm(prompt)
    except Exception as exc:
        llm_response["error"] = str(exc)

    # 5. Parse LLM response into structured suspects
    ai_suspects = _parse_llm_response(llm_response.get("content", ""), mods)

    # 6. Merge local + AI results (deduplicate, sort by confidence)
    all_suspects = _merge_suspects(local_hits, ai_suspects)

    explanation = llm_response.get("content", "")
    if llm_response.get("error") and not explanation:
        explanation = f"(LLM no disponible: {llm_response['error'][:120]}. Mostrando solo resultados locales.)"

    return {
        "suspects": all_suspects,
        "explanation": explanation,
        "tokens_used": llm_response.get("tokens_used"),
        "web_sources": [r.get("url", "") for r in web_results if r.get("url")],
    }


def _build_prompt(
    mods: list[str],
    plugins: list[str],
    bug: str,
    game: str,
    local_hits: list[dict],
    web_results: list[dict],
) -> str:
    mod_list_str = "\n".join(f"- {m}" for m in mods[:80])
    plugin_list_str = "\n".join(f"- {p}" for p in plugins[:80])

    local_str = ""
    if local_hits:
        local_str = "\n\nLocal knowledge base flagged these suspects:\n"
        local_str += "\n".join(f"- {h['mod']} ({int(h['confidence']*100)}%): {h['fix']}" for h in local_hits)

    web_str = format_search_results_for_prompt(web_results)

    return f"""You are an expert modding assistant for {game}.
A user reported the following bug:
"{bug}"

Installed mods:
{mod_list_str}

Active plugins (load order):
{plugin_list_str}
{local_str}
{web_str}

Instructions:
1. Use the real-time search results above as primary evidence — these are actual community reports.
2. Identify which mods are most likely causing this bug based on search results + your knowledge.
3. For each suspect mod, provide: mod name, confidence (0.0-1.0), reason, and a specific fix.
4. Be honest: if the search results mention a specific fix or workaround, use it.
5. Give a brief overall explanation in the same language the user used.
6. At the END of your response, output a JSON array inside ```json ... ``` with suspects:
   [{{"mod": "...", "confidence": 0.0, "reason": "...", "fix": "..."}}]
"""


def _parse_llm_response(content: str, mods: list[str]) -> list[dict]:
    import re
    suspects = []
    match = re.search(r"```json\s*(.*?)```", content, re.DOTALL)
    if not match:
        return suspects
    try:
        data = json.loads(match.group(1))
        if isinstance(data, list):
            for item in data:
                suspects.append({
                    "mod": item.get("mod", "Unknown"),
                    "confidence": float(item.get("confidence", 0.5)),
                    "reason": item.get("reason", ""),
                    "fix": item.get("fix"),
                })
    except (json.JSONDecodeError, ValueError):
        pass
    return suspects


def _merge_suspects(local: list[dict], ai: list[dict]) -> list[dict]:
    seen = {}
    for s in local + ai:
        key = s["mod"].lower()
        if key not in seen or s["confidence"] > seen[key]["confidence"]:
            seen[key] = s
    return sorted(seen.values(), key=lambda x: x["confidence"], reverse=True)
