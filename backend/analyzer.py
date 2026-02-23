"""
Core analysis logic: local heuristics + real-time web search + LLM with full environment context.
"""

import json
import logging
from typing import Optional

from .llm import call_llm
from .knowledge import load_knowledge_base, local_heuristic_search
from .web_search import search_with_queries, format_search_results_for_prompt
from .local_investigator import investigate
from .search_planner import generate_search_queries, extract_filter_words

log = logging.getLogger(__name__)
KB = load_knowledge_base()


def _prefilter_mods(mods: list[str], bug: str, file_conflicts: list[dict], priority_mods: list[str]) -> list[str]:
    """
    Mods relevantes: conflictos reales + mods que comparten palabras con el bug + priority del investigador.
    Sin hardcode.
    """
    relevant = set()

    # 1. Conflictos de archivos
    for c in file_conflicts[:50]:
        for m in c.get("mods", []):
            relevant.add(m)

    # 2. Mods cuya nombre contiene palabra del bug (3+ chars)
    bug_words = {w.lower() for w in bug.split() if len(w) >= 3}
    for mod in mods:
        m = mod.lower()
        if any(w in m for w in bug_words):
            relevant.add(mod)

    # 3. Prioridad del investigador
    relevant.update(priority_mods[:15])

    # 4. Primeros mods si muy pocos
    if len(relevant) < 8:
        relevant.update(mods[:25])

    return [m for m in mods if m in relevant][:45]


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
    include_web_search: bool = True,
) -> dict:
    # 1. Investigador local: analiza archivos (sin hardcode)
    inv = investigate(
        bug_description,
        file_conflicts or [],
        overwrite_files or [],
        mods,
    )
    log.info(f"Investigator brief: {inv['brief'][:80]}...")

    # 2. Prefilter mods (dinámico: conflictos + palabras del bug)
    relevant_mods = _prefilter_mods(mods, bug_description, file_conflicts or [], inv.get("priority_mods", []))
    log.info(f"Mods: {len(mods)} → {len(relevant_mods)} relevant")

    # 3. LLM genera queries + filter keywords (cero hardcode)
    search_queries = []
    filter_words = []
    if include_web_search:
        search_queries, filter_words = await generate_search_queries(bug_description, relevant_mods)
        log.info(f"Queries: {search_queries[:3]}, filter: {filter_words[:4]}")

    # 4. Búsqueda: scraper + Reddit, filtrada por keywords del LLM
    local_hits = local_heuristic_search(mods, bug_description, KB)
    web_results = []
    if include_web_search and search_queries:
        try:
            web_results = await search_with_queries(
                search_queries,
                bug_description,
                filter_words=filter_words,
            )
            log.info(f"Web search: {len(web_results)} results, {len([r for r in web_results if r.get('url')])} with URLs")
        except Exception as exc:
            log.warning(f"Web search failed: {exc}")

    prompt = _build_prompt(
        mods=relevant_mods,
        plugins=plugins,
        bug=bug_description,
        game=game,
        local_hits=local_hits,
        web_results=web_results,
        investigation_brief=inv["brief"],
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

    # Extraer URLs - SIEMPRE incluir todas las que tengamos
    urls = []
    for r in web_results:
        u = r.get("url") or r.get("URL") or ""
        if u and str(u).startswith("http"):
            urls.append(str(u))
    urls = list(dict.fromkeys(urls))  # dedupe manteniendo orden

    log.info(f"Returning {len(urls)} web_sources to client")
    return {
        "suspects": all_suspects,
        "explanation": explanation,
        "tokens_used": llm_response.get("tokens_used"),
        "web_sources": urls,
        "investigation_brief": inv["brief"],
    }


def _build_prompt(
    mods, plugins, bug, game, local_hits, web_results,
    investigation_brief: str,
    load_order, file_conflicts, overwrite_files, mod_metadata,
    skyrim_version, skse_version, papyrus_errors, skse_errors,
    response_language: str = "auto",
) -> str:
    sections = []

    # Header
    sections.append(f'You are an expert {game} modding assistant. A user reports this bug:\n"{bug}"')

    # Resumen del investigador local (análisis de archivos/conflictos)
    if investigation_brief:
        sections.append(f"LOCAL INVESTIGATION (file/conflict analysis):\n{investigation_brief}")

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
        "2. ONLY suggest mods that could PLAUSIBLY cause THIS specific bug.\n"
        "   Use LOCAL INVESTIGATION and WEB SEARCH RESULTS to inform your answer.\n"
        "3. Prioritize mods in file conflicts that match the bug type.\n"
        "4. The WEB SEARCH RESULTS include URLs — the user will see these as Fuentes/Links.\n"
        "5. Assign confidence based on evidence (file conflicts + web posts + mod relevance).\n"
        f"6. {lang_instruction}\n"
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
