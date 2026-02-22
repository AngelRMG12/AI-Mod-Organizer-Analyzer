"""
Prueba rápida del análisis local sin necesidad de MO2 ni backend.
Ejecutar: python test_local.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.knowledge import load_knowledge_base, local_heuristic_search

KB = load_knowledge_base()

TEST_CASES = [
    {
        "bug": "NPCs tienen la cara negra",
        "mods": ["Bijin NPCs", "RaceMenu", "FNIS", "XP32 Maximum Skeleton", "USSEP", "CBBE"],
    },
    {
        "bug": "Mi personaje está en T-pose cuando usa animaciones",
        "mods": ["FNIS", "Nemesis", "XP32 Maximum Skeleton", "CBBE", "SkyUI"],
    },
    {
        "bug": "Game crashes when entering Whiterun CTD",
        "mods": ["ENB", "SKSE", "Unofficial Skyrim Patch", "Immersive Citizens", "Realistic Water Two"],
    },
    {
        "bug": "Missing textures on armor mods",
        "mods": ["BodySlide", "CBBE", "UNP", "SKSE", "SkyUI"],
    },
]

print("=" * 60)
print("  AI Conflict Analyzer — Prueba local (sin backend/MO2)")
print("=" * 60)

for i, case in enumerate(TEST_CASES, 1):
    print(f"\n[Caso {i}] Bug: \"{case['bug']}\"")
    print(f"Mods instalados: {', '.join(case['mods'])}")
    suspects = local_heuristic_search(case["mods"], case["bug"], KB)
    if suspects:
        print("Sospechosos encontrados:")
        for s in sorted(suspects, key=lambda x: x["confidence"], reverse=True):
            pct = int(s["confidence"] * 100)
            print(f"  [{pct}%] {s['mod']}")
            print(f"        Razón: {s['reason']}")
            print(f"        Fix:   {s['fix']}")
    else:
        print("  Sin coincidencias en la knowledge base local.")

print("\n" + "=" * 60)
print("Prueba completada. Para análisis con IA, levanta el backend.")
print("=" * 60)
