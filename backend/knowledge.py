"""
Knowledge base loader and local heuristic search.
"""

import json
from pathlib import Path

KB_PATH = Path(__file__).parent.parent / "knowledge_base" / "conflicts.json"


def load_knowledge_base() -> dict:
    if KB_PATH.exists():
        with open(KB_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def local_heuristic_search(mods: list[str], bug_description: str, kb: dict) -> list[dict]:
    """
    Offline heuristic pass. Checks bug description keywords against the
    knowledge base and returns matching mods with confidence scores.
    """
    suspects = []
    bug_lower = bug_description.lower()

    for bug_key, conflict_info in kb.items():
        if bug_key.lower() in bug_lower:
            related_mods = conflict_info.get("mods", [])
            fix = conflict_info.get("fix", "No local fix available.")
            confidence = conflict_info.get("confidence", 0.6)
            for mod in mods:
                for keyword in related_mods:
                    if keyword.lower() in mod.lower():
                        suspects.append({
                            "mod": mod,
                            "confidence": confidence,
                            "reason": f"Known conflict pattern: '{bug_key}'",
                            "fix": fix,
                        })
    return suspects
