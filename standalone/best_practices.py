"""
Buenas prácticas de modding para Skyrim SE.
Checklist y links útiles.
"""

BEST_PRACTICES = [
    {
        "name": "Engine Fixes",
        "desc": "Parches críticos para estabilidad (memory, save corrupt, etc.)",
        "link": "https://www.nexusmods.com/skyrimspecialedition/mods/17230",
        "keywords": ["engine", "crash", "memory", "ctd"],
    },
    {
        "name": "Crash Logger",
        "desc": "Log de crashes para diagnosticar CTDs",
        "link": "https://www.nexusmods.com/skyrimspecialedition/mods/59818",
        "keywords": ["crash", "ctd", "log"],
    },
    {
        "name": "Address Library / SSE Address Library",
        "desc": "Requerido por muchos SKSE plugins",
        "link": "https://www.nexusmods.com/skyrimspecialedition/mods/32444",
        "keywords": ["address", "skse", "plugin"],
    },
    {
        "name": "LOOT",
        "desc": "Ordena plugins automáticamente (evita conflictos de load order)",
        "link": "https://loot.github.io/",
        "keywords": ["load", "order", "conflict"],
    },
    {
        "name": "SKSE versión correcta",
        "desc": "SKSE debe coincidir con tu versión de Skyrim (ej: 1.6.1170 → SKSE 2.2.6)",
        "link": "https://skse.silverlock.org/",
        "keywords": ["skse", "versión", "crash", "no inicia"],
    },
    {
        "name": "BethINI",
        "desc": "Optimiza skyrim.ini y skyrimprefs.ini",
        "link": "https://www.nexusmods.com/skyrimspecialedition/mods/4875",
        "keywords": ["ini", "performance", "rendimiento"],
    },
    {
        "name": "SSE Edit / xEdit",
        "desc": "Edita y limpia plugins (AutoClean), merge, conflict resolution",
        "link": "https://www.nexusmods.com/skyrimspecialedition/mods/164",
        "keywords": ["conflict", "clean", "merge", "edit"],
    },
    {
        "name": "Animation mods: Nemesis",
        "desc": "Para animaciones custom (reemplaza FNIS en muchos casos)",
        "link": "https://www.nexusmods.com/skyrimspecialedition/mods/60033",
        "keywords": ["animación", "t-pose", "fnis", "nemesis"],
    },
    {
        "name": "Body mods: BodySlide",
        "desc": "Construir bodies y ropa (CBBE, UNP, etc.)",
        "link": "https://www.nexusmods.com/skyrimspecialedition/mods/201",
        "keywords": ["body", "cbbe", "unp", "ropaje"],
    },
    {
        "name": "Guía r/skyrimmods",
        "desc": "Wiki con guías de instalación y troubleshooting",
        "link": "https://www.reddit.com/r/skyrimmods/wiki/",
        "keywords": [],
    },
]



def suggest_plugin_order(plugins: list[str]) -> list[str]:
    """
    Sugiere un orden más seguro para plugins (heurística simple).
    No reemplaza LOOT pero da una base decente.
    """
    def score(p: str) -> tuple:
        pl = p.lower()
        # Masters
        if pl.endswith(".esm"):
            if "skyrim" in pl and "update" not in pl and "dawnguard" not in pl and "dragonborn" not in pl and "hearthfires" not in pl:
                return (0, pl)
            if "update" in pl:
                return (1, pl)
            if "dawnguard" in pl:
                return (2, pl)
            if "hearthfires" in pl:
                return (3, pl)
            if "dragonborn" in pl:
                return (4, pl)
            return (5, pl)
        # ESP/ESL
        if "patch" in pl or "compatibility" in pl or "compat" in pl:
            return (90, pl)
        if pl.startswith("ussep") or pl.startswith("unofficial skyrim"):
            return (10, pl)
        if "merge" in pl or "bashed" in pl or "smashed" in pl:
            return (100, pl)
        return (50, pl)

    return sorted(plugins, key=score)
