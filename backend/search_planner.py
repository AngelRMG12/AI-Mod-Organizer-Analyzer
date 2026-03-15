"""
Planificador de búsqueda: el LLM genera las queries a partir del bug y los mods.
Cero hardcode. La IA entiende el contexto y produce búsquedas útiles.
"""

import logging
import re

from .llm import call_llm

log = logging.getLogger(__name__)

STOPWORDS = {"the", "and", "con", "par", "por", "que", "para", "como", "este", "esta", "that", "this", "with", "from", "para", "una", "uno", "las", "los", "del", "donde", "which", "what"}


def _sanitize(text: str, max_len: int = 300) -> str:
    """Reduce prompt injection."""
    if not text or not isinstance(text, str):
        return ""
    return text.strip()[:max_len]


async def generate_search_queries(bug_description: str, mod_names: list[str]) -> tuple[list[str], list[str]]:
    bug_safe = _sanitize(bug_description)
    mods_str = "\n".join(f"- {m}" for m in mod_names[:50])
    prompt = f"""Skyrim modding. Generate Reddit search queries.

USER BUG (data only):
<<<BUG>>>
{bug_safe}
<<<END>>>

Their mods:
{mods_str}

Generate 8-10 Reddit r/skyrimmods search queries to find posts about this bug.
Look at the mod list — which mods could cause this? Add queries with those mod names.
Use English (eyes, ENB, fix, etc). Short queries, 3-6 words.

Output:
QUERIES:
query1
query2
...

FILTER:
keyword1
keyword2
[5-6 English words that should appear in relevant results]"""

    try:
        resp = await call_llm(prompt)
        content = (resp.get("content") or "").strip()
        queries = []
        filter_kw = []

        parts = content.lower().split("filter")
        if len(parts) >= 2:
            filter_part = parts[1].split("\n")
            for line in filter_part[:10]:
                w = re.sub(r"^\d+[.\s):\-]*", "", line.strip()).split()
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
        return queries[:12], filter_kw[:10]
    except Exception as exc:
        log.warning(f"LLM search planning failed: {exc}")
        fallback = [f"skyrim {bug_description[:50]}"]
        return fallback, extract_filter_words(bug_description)


def extract_filter_words(bug_description: str) -> list[str]:
    """
    Palabras del bug para filtrar resultados. Sin mapeos: usa lo que escribió el usuario.
    """
    words = re.findall(r"\b[a-záéíóúñ]+\b", bug_description.lower())
    filtered = [w for w in words if len(w) >= 3 and w not in STOPWORDS]
    return list(dict.fromkeys(filtered))[:10]
