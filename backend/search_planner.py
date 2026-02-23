"""
Planificador de búsqueda: el LLM genera las queries a partir del bug y los mods.
Cero hardcode. La IA entiende el contexto y produce búsquedas útiles.
"""

import logging
import re

from .llm import call_llm

log = logging.getLogger(__name__)

STOPWORDS = {"the", "and", "con", "par", "por", "que", "para", "como", "este", "esta", "that", "this", "with", "from", "para", "una", "uno", "las", "los", "del", "donde", "which", "what"}


async def generate_search_queries(bug_description: str, mod_names: list[str]) -> tuple[list[str], list[str]]:
    """
    El LLM analiza el bug y los mods. Devuelve (queries, filter_keywords).
    Filter keywords en inglés para que matcheen posts de Reddit.
    """
    mods_str = "\n".join(f"- {m}" for m in mod_names[:25])
    prompt = f"""You are a Skyrim modding expert. A user reports this bug (any language):

"{bug_description}"

Their mods: {mods_str[:800]}

Output in this exact format:

QUERIES:
skyrim enb eyes
ENB Dynamic Cubemaps eyes skyrim
[4-5 more short queries, 3-6 words each]

FILTER:
eyes
enb
white
reflective
[3-5 keywords that should appear in relevant Reddit post titles. Use English.]"""

    try:
        resp = await call_llm(prompt)
        content = (resp.get("content") or "").strip()
        queries = []
        filter_kw = []

        parts = content.lower().split("filter")
        if len(parts) >= 2:
            filter_part = parts[1].split("\n")
            for line in filter_part[:10]:
                w = re.sub(r"^\d+[\.\):\s-*]*", "", line.strip()).split()
                if w and len(w[0]) >= 2:
                    filter_kw.append(w[0][:30])

        for line in content.split("\n"):
            line = line.strip()
            if "filter" in line.lower() or "queries" in line.lower():
                continue
            q = re.sub(r"^\d+[\.\)]\s*", "", line).strip().lstrip("-* ")
            if q and 5 < len(q) < 120 and "\n" not in q:
                queries.append(q)
                if len(queries) >= 8:
                    break

        if not filter_kw:
            filter_kw = extract_filter_words(bug_description)

        log.info(f"LLM: {len(queries)} queries, {len(filter_kw)} filter")
        return queries[:8], filter_kw[:8]
    except Exception as exc:
        log.warning(f"LLM search planning failed: {exc}")
        return [f"skyrim {bug_description[:50]}"], extract_filter_words(bug_description)


def extract_filter_words(bug_description: str) -> list[str]:
    """
    Palabras del bug para filtrar resultados. Sin mapeos: usa lo que escribió el usuario.
    """
    words = re.findall(r"\b[a-záéíóúñ]+\b", bug_description.lower())
    filtered = [w for w in words if len(w) >= 3 and w not in STOPWORDS]
    return list(dict.fromkeys(filtered))[:10]
