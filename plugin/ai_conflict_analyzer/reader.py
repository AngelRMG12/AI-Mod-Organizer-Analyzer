"""
MO2 environment reader.
Collects everything the AI needs to give an accurate diagnosis:
  - modlist.txt / plugins.txt / loadorder.txt
  - Real file conflicts between mods (same file path in two active mods)
  - Overwrite folder contents
  - Skyrim version (from SkyrimSE.exe / Skyrim.exe)
  - SKSE version
  - Papyrus script logs (crash/error reports)
  - Mod metadata (version, Nexus ID from each mod's meta.ini)
"""

import os
import re
import configparser
from pathlib import Path
from typing import Optional


# --------------------------------------------------------------------------- #
# Basic profile files                                                           #
# --------------------------------------------------------------------------- #

def read_modlist(profile_path: Path) -> list[str]:
    """Returns all active mods (lines starting with '+')."""
    mods = []
    modlist_file = profile_path / "modlist.txt"
    if not modlist_file.exists():
        return mods
    with open(modlist_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("+"):
                mods.append(line[1:].strip())
    return mods


def read_plugins(profile_path: Path) -> list[str]:
    """Returns all enabled plugins (lines starting with '*')."""
    plugins = []
    plugins_file = profile_path / "plugins.txt"
    if not plugins_file.exists():
        return plugins
    with open(plugins_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("*"):
                plugins.append(line[1:].strip())
            elif line and not line.startswith("#"):
                plugins.append(line)
    return plugins


def read_load_order(profile_path: Path) -> list[str]:
    """Returns exact load order from loadorder.txt."""
    order = []
    loadorder_file = profile_path / "loadorder.txt"
    if not loadorder_file.exists():
        return order
    with open(loadorder_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                order.append(line)
    return order


# --------------------------------------------------------------------------- #
# Real file conflicts between mods                                              #
# --------------------------------------------------------------------------- #

def find_file_conflicts(mods_base_path: Path, active_mods: list[str]) -> list[dict]:
    """
    Scans each active mod's folder and finds files that exist in more than one mod.
    These are REAL conflicts — the mod lower in the list wins (MO2 behavior).

    Returns a list of:
      {
        "file": "meshes/actors/character/...",
        "mods": ["ModA", "ModB"],   # all mods that have this file
        "winner": "ModB"            # the mod that actually loads (first in active_mods = highest priority)
      }
    """
    if not mods_base_path.exists():
        return []

    # Map: relative_file_path → list of mods that contain it
    file_to_mods: dict[str, list[str]] = {}

    for mod_name in active_mods:
        mod_path = mods_base_path / mod_name
        if not mod_path.is_dir():
            continue
        for file in mod_path.rglob("*"):
            if file.is_file():
                relative = str(file.relative_to(mod_path)).lower()
                # Skip meta files
                if relative in ("meta.ini", "readme.txt", "readme.md"):
                    continue
                file_to_mods.setdefault(relative, []).append(mod_name)

    conflicts = []
    for rel_path, mods in file_to_mods.items():
        if len(mods) > 1:
            # Winner = first mod in active_mods list that has this file (lowest index = highest priority in MO2)
            winner = next((m for m in active_mods if m in mods), mods[0])
            conflicts.append({
                "file": rel_path,
                "mods": mods,
                "winner": winner,
            })

    return conflicts


def find_overwrite_files(mo2_base_path: Path) -> list[str]:
    """Returns files sitting in MO2's overwrite folder (unmanaged overrides)."""
    overwrite_dir = mo2_base_path / "overwrite"
    files = []
    if not overwrite_dir.exists():
        return files
    for file in overwrite_dir.rglob("*"):
        if file.is_file():
            files.append(str(file.relative_to(overwrite_dir)))
    return files


# --------------------------------------------------------------------------- #
# Mod metadata (meta.ini in each mod folder)                                   #
# --------------------------------------------------------------------------- #

# Nexus Mods category IDs → readable names (Skyrim SE / general)
_NEXUS_CATEGORIES = {
    "5": "Armour", "6": "Audio", "8": "Clothing", "9": "Combat",
    "10": "Creatures", "12": "Followers", "15": "Gameplay",
    "17": "Graphics", "18": "Hair and Face", "21": "Items",
    "22": "Items - World", "24": "Landscape", "25": "Lore and Quests",
    "26": "Magic", "27": "Spells", "28": "Miscellaneous",
    "30": "Models and Textures", "32": "NPC", "34": "Patches",
    "39": "Races", "40": "Quests", "43": "Sounds and Music",
    "46": "Utilities", "49": "Weapons", "51": "User Interface",
    "55": "Clothing - Armour", "56": "Animation", "57": "Companions",
    "66": "ENBSeries", "67": "Followers",
}

def read_mod_metadata(mods_base_path: Path, mod_name: str) -> dict:
    """
    Reads the meta.ini that MO2 creates for each installed mod.
    Contains: version, Nexus mod ID, category, install date.
    """
    meta_file = mods_base_path / mod_name / "meta.ini"
    info = {"name": mod_name, "version": None, "nexus_id": None, "category": None}
    if not meta_file.exists():
        return info

    cfg = configparser.ConfigParser()
    try:
        cfg.read(str(meta_file), encoding="utf-8")
        general = cfg["General"] if "General" in cfg else {}
        info["version"] = general.get("version") or general.get("Version")
        info["nexus_id"] = general.get("modid") or general.get("ModID")
        raw_cat = general.get("category") or general.get("Category") or ""
        # Nexus stores category as a numeric ID — convert to readable name
        info["category"] = _NEXUS_CATEGORIES.get(str(raw_cat).strip(), raw_cat) or None
    except Exception:
        pass
    return info


def read_all_mod_metadata(mods_base_path: Path, active_mods: list[str]) -> list[dict]:
    """Reads metadata for all active mods."""
    return [read_mod_metadata(mods_base_path, m) for m in active_mods]


# --------------------------------------------------------------------------- #
# Game version detection                                                        #
# --------------------------------------------------------------------------- #

def get_skyrim_version(game_path: Path) -> Optional[str]:
    """
    Reads the version of SkyrimSE.exe / Skyrim.exe using Windows API.
    Returns version string like "1.6.1170.0" or None.
    """
    for exe_name in ("SkyrimSE.exe", "Skyrim.exe", "Fallout4.exe", "FalloutNV.exe"):
        exe_path = game_path / exe_name
        if exe_path.exists():
            try:
                import win32api
                info = win32api.GetFileVersionInfo(str(exe_path), "\\")
                ms = info["FileVersionMS"]
                ls = info["FileVersionLS"]
                version = f"{ms >> 16}.{ms & 0xFFFF}.{ls >> 16}.{ls & 0xFFFF}"
                return f"{exe_name} {version}"
            except Exception:
                # Fallback: try reading from file metadata without win32api
                try:
                    import struct
                    with open(exe_path, "rb") as f:
                        data = f.read(1024 * 512)  # read first 512KB
                    # Look for VS_VERSION_INFO pattern
                    marker = b"V\x00S\x00_\x00V\x00E\x00R\x00S\x00I\x00O\x00N\x00_\x00I\x00N\x00F\x00O"
                    idx = data.find(marker)
                    if idx > 0:
                        offset = idx + 0x28
                        nums = struct.unpack_from("<4H", data, offset)
                        return f"{exe_name} {nums[1]}.{nums[0]}.{nums[3]}.{nums[2]}"
                except Exception:
                    return f"{exe_name} (version unreadable)"
    return None


def get_skse_version(game_path: Path) -> Optional[str]:
    """Detects SKSE version from skse64_*.dll filename (version is in the name)."""
    if not game_path.exists():
        return None
    for file in game_path.glob("skse64_*.dll"):
        match = re.search(r"skse64_(\d+_\d+_\d+)", file.name)
        if match:
            version = match.group(1).replace("_", ".")
            return f"SKSE64 {version}"
    if (game_path / "skse_loader.exe").exists():
        return "SKSE (version unknown)"
    return None


# --------------------------------------------------------------------------- #
# Papyrus logs (script errors / crash reports)                                 #
# --------------------------------------------------------------------------- #

def read_papyrus_logs(game_docs_path: Path, max_lines: int = 100) -> list[str]:
    """
    Reads Papyrus script logs from:
      Documents/My Games/Skyrim Special Edition/Logs/Script/Papyrus.0.log
    Returns the last N lines (most recent errors).
    """
    log_paths = [
        game_docs_path / "Logs" / "Script" / "Papyrus.0.log",
        game_docs_path / "Logs" / "Script" / "User" / "Papyrus.0.log",
    ]
    for log_path in log_paths:
        if log_path.exists():
            try:
                with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
                # Return only error/warning lines + last few lines for context
                important = [
                    l.strip() for l in lines
                    if any(kw in l for kw in ["error", "Error", "WARNING", "Cannot", "cannot", "failed", "FAULT"])
                ]
                return important[-max_lines:] if len(important) > max_lines else important
            except Exception:
                pass
    return []


def read_skse_logs(game_docs_path: Path) -> list[str]:
    """Reads SKSE log files for plugin errors."""
    skse_log_dir = game_docs_path / "SKSE"
    errors = []
    if not skse_log_dir.exists():
        return errors
    for log_file in skse_log_dir.glob("*.log"):
        try:
            with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if any(kw in line for kw in ["error", "Error", "failed", "crash", "FATAL"]):
                        errors.append(f"[{log_file.name}] {line.strip()}")
        except Exception:
            pass
    return errors[-50:]


# --------------------------------------------------------------------------- #
# Convenience: collect everything in one call                                   #
# --------------------------------------------------------------------------- #

def collect_environment(
    profile_path: Path,
    mo2_base_path: Path,
    game_path: Optional[Path] = None,
    game_docs_path: Optional[Path] = None,
    include_file_conflicts: bool = True,
) -> dict:
    """
    Collects all available data from the MO2 environment.
    Returns a dict ready to be sent to the backend /analyze endpoint.
    """
    active_mods = read_modlist(profile_path)
    plugins = read_plugins(profile_path)
    load_order = read_load_order(profile_path)
    mods_path = mo2_base_path / "mods"

    file_conflicts = []
    if include_file_conflicts and mods_path.exists():
        # Limit to avoid sending thousands of conflicts — focus on important file types
        all_conflicts = find_file_conflicts(mods_path, active_mods)
        priority_exts = {".esp", ".esm", ".esl", ".nif", ".dds", ".psc", ".pex", ".dll", ".skse"}
        file_conflicts = [
            c for c in all_conflicts
            if any(c["file"].endswith(ext) for ext in priority_exts)
        ][:100]  # cap at 100 most important

    overwrite = find_overwrite_files(mo2_base_path)
    mod_metadata = read_all_mod_metadata(mods_path, active_mods)

    skyrim_version = None
    skse_version = None
    papyrus_errors = []
    skse_errors = []

    if game_path:
        skyrim_version = get_skyrim_version(game_path)
        skse_version = get_skse_version(game_path)

    if game_docs_path:
        papyrus_errors = read_papyrus_logs(game_docs_path)
        skse_errors = read_skse_logs(game_docs_path)

    return {
        "mods": active_mods,
        "plugins": plugins,
        "load_order": load_order,
        "file_conflicts": file_conflicts,
        "overwrite_files": overwrite[:50],
        "mod_metadata": mod_metadata,
        "skyrim_version": skyrim_version,
        "skse_version": skse_version,
        "papyrus_errors": papyrus_errors[:50],
        "skse_errors": skse_errors[:30],
    }
