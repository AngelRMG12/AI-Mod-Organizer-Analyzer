"""
Escaneo profundo de carpetas de Mod Organizer.
Investiga archivos reales en los mods: rutas, readmes, meta.ini.
Da al LLM contexto de qué archivos tocan qué (ojos, ENB, caras, etc.).
"""

import configparser
import re
from pathlib import Path
from typing import Optional

# Extensiones y rutas que suelen relacionarse con bugs visuales
RELEVANT_PATHS = [
    "eye", "eyes", "face", "head", "character", "npc",
    "mesh", "meshes", "texture", "textures",
    "enb", "cubemap", "dynamic", "skeleton", "skeletal",
    "animation", "anim", "hair", "skin", "body",
    "enbseries", "effect", "shader",
]
RELEVANT_EXTS = {".nif", ".dds", ".tri", ".hkx", ".esp", ".esm", ".ini"}


def _bug_keywords(bug: str) -> set[str]:
    """Extrae palabras clave del bug para filtrar archivos relevantes."""
    words = set()
    # Palabras directas
    for w in re.findall(r"[a-zA-Z]{3,}", bug.lower()):
        words.add(w)
    # Mapeos comunes
    if "ojo" in bug.lower() or "eye" in bug.lower():
        words.update(["eye", "eyes"])
    if "cara" in bug.lower() or "face" in bug.lower():
        words.update(["face", "head", "character"])
    if "blanco" in bug.lower() or "white" in bug.lower():
        words.add("eye")  # ojos blancos
    if "enb" in bug.lower():
        words.update(["enb", "cubemap", "dynamic"])
    if "reflect" in bug.lower():
        words.update(["cubemap", "dynamic"])
    return words


def _path_matches(path_lower: str, keywords: set[str]) -> bool:
    """Ruta contiene path relevante o keyword del bug."""
    for kw in keywords:
        if kw in path_lower:
            return True
    for rp in RELEVANT_PATHS:
        if rp in path_lower:
            return True
    return False


def _read_text_safe(path: Path, max_chars: int = 500, encoding: str = "utf-8") -> str:
    """Lee archivo de texto con fallback a latin-1."""
    try:
        data = path.read_bytes()
        for enc in (encoding, "utf-8", "latin-1", "cp1252"):
            try:
                return data.decode(enc, errors="ignore")[:max_chars]
            except Exception:
                continue
    except Exception:
        pass
    return ""


def _read_mod_description(mod_path: Path) -> str:
    """Lee descripción del mod: meta.ini, readme, etc."""
    parts = []

    # meta.ini (MO2 guarda descripción ahí)
    meta = mod_path / "meta.ini"
    if meta.exists():
        try:
            cfg = configparser.ConfigParser()
            cfg.read(str(meta), encoding="utf-8")
            if "General" in cfg:
                desc = cfg["General"].get("description") or cfg["General"].get("notes", "")
                if desc:
                    parts.append(f"meta.ini: {desc[:300]}")
        except Exception:
            pass

    # README
    for name in ("readme.txt", "Readme.txt", "README.md", "readme.md", "description.txt"):
        p = mod_path / name
        if p.exists() and p.is_file():
            text = _read_text_safe(p, 400)
            if text and len(text.strip()) > 20:
                # Solo primeras líneas útiles
                lines = [l.strip() for l in text.split("\n") if l.strip()][:15]
                parts.append(f"{name}: " + " | ".join(lines))
            break

    return " | ".join(parts)[:500] if parts else ""


def _scan_mod_files(mod_path: Path, keywords: set[str], max_files: int = 35) -> list[str]:
    """Lista archivos del mod cuya ruta coincide con keywords o rutas relevantes."""
    found = []
    try:
        for f in mod_path.rglob("*"):
            if len(found) >= max_files:
                break
            if not f.is_file():
                continue
            rel = str(f.relative_to(mod_path)).lower()
            ext = f.suffix.lower()
            if ext in RELEVANT_EXTS or _path_matches(rel, keywords):
                found.append(rel.replace("\\", "/"))
    except Exception:
        pass
    return found[:max_files]


def _scan_mod_folders(mod_path: Path, keywords: set[str]) -> list[str]:
    """Resumen de carpetas relevantes (meshes/actors/character/eyes, etc.)."""
    dirs = set()
    try:
        for d in mod_path.rglob("*"):
            if not d.is_dir():
                continue
            rel = str(d.relative_to(mod_path)).lower()
            if _path_matches(rel, keywords):
                # Acortar: meshes/actors/character/eyes/...
                parts = rel.replace("\\", "/").split("/")
                if len(parts) <= 4:
                    dirs.add(rel.replace("\\", "/"))
                else:
                    dirs.add("/".join(parts[:4]) + "/...")
    except Exception:
        pass
    return sorted(dirs)[:15]


def scan_mod_folders(
    mods_base_path: Path,
    active_mods: list[str],
    bug_description: str,
    max_mods_to_scan: int = 25,
    mods_to_prioritize: Optional[list[str]] = None,
) -> str:
    """
    Escanea carpetas de MO2 y devuelve un resumen para el LLM.
    Investiga mods relevantes al bug: archivos, carpetas, readmes.
    """
    if not mods_base_path.exists():
        return ""

    keywords = _bug_keywords(bug_description)
    priority_set = set((mods_to_prioritize or [])[:15])

    lines = []
    scanned = 0

    # Orden: primero los que coinciden con el bug o son prioritarios
    def score(mod: str) -> int:
        m = mod.lower()
        if mod in priority_set:
            return 100
        return sum(1 for kw in keywords if kw in m)

    to_scan = sorted(
        [m for m in active_mods if score(m) > 0] + active_mods[:30],
        key=score,
        reverse=True,
    )
    seen = set()
    for mod in to_scan:
        if mod in seen or scanned >= max_mods_to_scan:
            continue
        seen.add(mod)
        mod_path = mods_base_path / mod
        if not mod_path.is_dir():
            continue
        scanned += 1

        block = [f"--- MOD: {mod} ---"]

        desc = _read_mod_description(mod_path)
        if desc:
            block.append(f"Description: {desc}")

        files = _scan_mod_files(mod_path, keywords)
        if files:
            block.append(f"Relevant files ({len(files)}): " + ", ".join(files[:12]))
            if len(files) > 12:
                block.append(f"  ... and {len(files)-12} more")

        folders = _scan_mod_folders(mod_path, keywords)
        if folders:
            block.append(f"Relevant folders: {', '.join(folders[:8])}")

        if len(block) > 1:
            lines.append("\n".join(block))

    if not lines:
        return ""

    return (
        "DEEP FILE INVESTIGATION (scanned mod folders on disk):\n"
        + "\n\n".join(lines)
        + "\n\n(Use this to correlate mods with file paths related to the bug.)"
    )
