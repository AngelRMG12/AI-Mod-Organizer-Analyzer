"""
Core analysis logic: local heuristics + real-time web search + LLM with full environment context.
"""

import json
import logging
from typing import Optional

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
    load_order: Optional[list[str]] = None,
    file_conflicts: Optional[list[dict]] = None,
    overwrite_files: Optional[list[str]] = None,
    mod_metadata: Optional[list[dict]] = None,
    skyrim_version: Optional[str] = None,
    skse_version: Optional[str] = None,
    papyrus_errors: Optional[list[str]] = None,
    skse_errors: Optional[list[str]] = None,
    response_language: str = "auto",
) -> dict:
    # 1. Local heuristic pass
    local_hits = local_heuristic_search(mods, bug_description, KB)

    # 2. Real-time web search
    web_results = []
    try:
        web_results = await search_all(bug_description, mods)
        log.info(f"Web search: {len(web_results)} results")
    except Exception as exc:
        log.warning(f"Web search failed: {exc}")

    # 3. Build rich LLM prompt
    prompt = _build_prompt(
        mods=mods,
        plugins=plugins,
        bug=bug_description,
        game=game,
        local_hits=local_hits,
        web_results=web_results,
        load_order=load_order or [],
        file_conflicts=file_conflicts or [],
        overwrite_files=overwrite_files or [],
        mod_metadata=mod_metadata or [],
        skyrim_version=skyrim_version,
        skse_version=skse_version,
        papyrus_errors=papyrus_errors or [],
        skse_errors=skse_errors or [],
        response_language=response_language,
    )

    # 4. Call LLM
    llm_response = {"content": "", "tokens_used": None, "error": None}
    try:
        llm_response = await call_llm(prompt)
    except Exception as exc:
        llm_response["error"] = str(exc)

    # 5. Parse + merge
    ai_suspects = _parse_llm_response(llm_response.get("content", ""), mods)
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
    mods, plugins, bug, game, local_hits, web_results,
    load_order, file_conflicts, overwrite_files, mod_metadata,
    skyrim_version, skse_version, papyrus_errors, skse_errors,
    response_language: str = "auto",
) -> str:
    sections = []

    # Header
    sections.append(f'You are an expert {game} modding assistant. A user reports this bug:\n"{bug}"')

    # Game environment
    env_lines = []
    if skyrim_version:
        env_lines.append(f"Game version: {skyrim_version}")
    if skse_version:
        env_lines.append(f"SKSE: {skse_version}")
    if env_lines:
        sections.append("GAME ENVIRONMENT:\n" + "\n".join(env_lines))

    # Active mods (with version if available)
    meta_map = {m.get("name", ""): m for m in mod_metadata}
    mod_lines = []
    for mod in mods[:80]:
        meta = meta_map.get(mod, {})
        ver = meta.get("version")
        line = f"- {mod}" + (f" v{ver}" if ver else "")
        mod_lines.append(line)
    sections.append("ACTIVE MODS (" + str(len(mods)) + " total):\n" + "\n".join(mod_lines))

    # Load order
    if plugins:
        plugin_lines = "\n".join(f"- {p}" for p in plugins[:80])
        sections.append(f"PLUGIN LOAD ORDER:\n{plugin_lines}")

    # Real file conflicts (most important section)
    if file_conflicts:
        conflict_lines = []
        for c in file_conflicts[:40]:
            conflict_lines.append(
                f"- FILE: {c['file']}\n"
                f"  Conflict between: {', '.join(c['mods'])}\n"
                f"  Winner (loads last): {c['winner']}"
            )
        sections.append(
            f"REAL FILE CONFLICTS ({len(file_conflicts)} detected — these are actual overwrite conflicts):\n"
            + "\n".join(conflict_lines)
        )

    # Overwrite folder
    if overwrite_files:
        sections.append(
            f"OVERWRITE FOLDER ({len(overwrite_files)} unmanaged files):\n"
            + "\n".join(f"- {f}" for f in overwrite_files[:20])
        )

    # Papyrus errors (gold mine for diagnosis)
    if papyrus_errors:
        sections.append(
            f"PAPYRUS SCRIPT ERRORS ({len(papyrus_errors)} errors in log):\n"
            + "\n".join(papyrus_errors[:20])
        )

    # SKSE errors
    if skse_errors:
        sections.append(
            "SKSE ERRORS:\n" + "\n".join(skse_errors[:15])
        )

    # Local KB hints
    if local_hits:
        hints = "\n".join(f"- {h['mod']} ({int(h['confidence']*100)}%): {h['fix']}" for h in local_hits)
        sections.append(f"LOCAL KNOWLEDGE BASE HINTS:\n{hints}")

    # Web search results
    web_str = format_search_results_for_prompt(web_results)
    if web_str:
        sections.append(web_str)

    # Language instruction
    if response_language == "auto":
        lang_instruction = "Respond in the SAME language the user used in their bug description."
    else:
        lang_instruction = f"ALWAYS respond in {response_language}, regardless of the language used in the bug description."

    # Build the exact mod name list for the prompt so the LLM can't hallucinate
    mod_names_str = ", ".join(f'"{m}"' for m in mods[:80])

    sections.append(
        "CRITICAL RULES — FOLLOW EXACTLY:\n"
        f"1. ONLY use mod names from this list: [{mod_names_str}]\n"
        "   NEVER invent mod names like 'Mod XYZ', 'ModA', 'ABC' or any name not in the list above.\n"
        "2. Prioritize REAL FILE CONFLICTS and PAPYRUS ERRORS — these are hard evidence.\n"
        "3. Use web search results as supporting community evidence.\n"
        "4. Assign confidence 0.0-1.0 based on actual evidence, not guesses.\n"
        f"5. {lang_instruction}\n"
        "6. Be specific: mention exact files, exact positions, exact steps to fix.\n"
        "7. At the END output a JSON array in ```json ... ``` block:\n"
        '   [{"mod": "EXACT_MOD_NAME_FROM_LIST", "confidence": 0.0, "reason": "...", "fix": "..."}]'
    )

    return "\n\n".join(sections)


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
