"""
Core analysis logic: combines local heuristics + LLM call.
"""

import os
import json
from pathlib import Path
from typing import Optional

from .llm import call_llm
from .knowledge import load_knowledge_base, local_heuristic_search

KB = load_knowledge_base()


async def run_analysis(
    mods: list[str],
    plugins: list[str],
    bug_description: str,
    game: str = "Skyrim SE",
) -> dict:
    # 1. Local heuristic pass (fast, offline)
    local_hits = local_heuristic_search(mods, bug_description, KB)

    # 2. Build LLM prompt
    prompt = _build_prompt(mods, plugins, bug_description, game, local_hits)

    # 3. Call LLM
    llm_response = await call_llm(prompt)

    # 4. Parse LLM response into structured suspects
    ai_suspects = _parse_llm_response(llm_response.get("content", ""), mods)

    # 5. Merge local + AI results (deduplicate)
    all_suspects = _merge_suspects(local_hits, ai_suspects)

    return {
        "suspects": all_suspects,
        "explanation": llm_response.get("content", ""),
        "tokens_used": llm_response.get("tokens_used"),
    }


def _build_prompt(
    mods: list[str],
    plugins: list[str],
    bug: str,
    game: str,
    local_hits: list[dict],
) -> str:
    mod_list_str = "\n".join(f"- {m}" for m in mods[:80])  # limit to avoid token overflow
    plugin_list_str = "\n".join(f"- {p}" for p in plugins[:80])
    local_str = ""
    if local_hits:
        local_str = "\n\nLocal knowledge base already flagged these suspects:\n"
        local_str += "\n".join(f"- {h['mod']} ({int(h['confidence']*100)}%)" for h in local_hits)

    return f"""You are an expert modding assistant for {game}.
A user reported the following bug:
\"{bug}\"

Installed mods:
{mod_list_str}

Active plugins (load order):
{plugin_list_str}
{local_str}

Instructions:
1. Identify which mods are most likely causing this bug.
2. For each suspect mod, provide: mod name, confidence (0.0-1.0), reason, and suggested fix.
3. Give a brief overall explanation.
4. Format suspects as JSON array at the end of your response, enclosed in ```json ... ``` block.
   Each object: {{"mod": "...", "confidence": 0.0, "reason": "...", "fix": "..."}}
"""


def _parse_llm_response(content: str, mods: list[str]) -> list[dict]:
    """Extracts the JSON suspects block from the LLM response."""
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
