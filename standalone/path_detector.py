"""
Detecta rutas de Skyrim y Mod Organizer 2 en Windows.
Funciona como BodySlide/Nemesis: encuentra el juego y perfiles MO2.
"""

import os
import winreg
from pathlib import Path
from typing import Optional


def _get_reg_key(key: int, subkey: str, value: str = "Installed Path") -> Optional[str]:
    try:
        with winreg.OpenKey(key, subkey) as k:
            return winreg.QueryValueEx(k, value)[0]
    except Exception:
        return None


def detect_skyrim_path() -> Optional[Path]:
    """
    Detecta Skyrim SE/AE desde el Registry o variables de Steam.
    """
    # Bethesda Registry
    subkeys = [
        r"SOFTWARE\WOW6432Node\Bethesda Softworks\Skyrim Special Edition",
        r"SOFTWARE\Bethesda Softworks\Skyrim Special Edition",
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\Steam App 489830",
    ]
    for subkey in subkeys:
        val = _get_reg_key(winreg.HKEY_LOCAL_MACHINE, subkey, "Installed Path")
        if not val:
            val = _get_reg_key(winreg.HKEY_LOCAL_MACHINE, subkey, "InstallLocation")
        if val and Path(val).exists():
            return Path(val).resolve()

    # Steam común
    steam_paths = [
        Path(os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)")) / "Steam" / "steamapps" / "common" / "Skyrim Special Edition",
        Path(os.environ.get("PROGRAMFILES", "C:\\Program Files")) / "Steam" / "steamapps" / "common" / "Skyrim Special Edition",
    ]
    for p in steam_paths:
        if p.exists() and (p / "SkyrimSE.exe").exists():
            return p.resolve()

    return None


def detect_mo2_paths() -> list[Path]:
    """
    Busca instalaciones de Mod Organizer 2 en lugares comunes.
    No hace rglob en todo el disco (muy lento).
    """
    candidates = []
    common = [
        Path.home() / "Mod Organizer 2",
        Path.home() / "ModOrganizer2",
        Path.home() / "Downloads" / "Mod Organizer 2",
        Path.home() / "AppData" / "Local" / "ModOrganizer",
        Path("C:/Mod Organizer 2"),
        Path("D:/Mod Organizer 2"),
    ]
    # Si Skyrim está en Steam, MO2 suele estar cerca
    steam = Path(os.environ.get("PROGRAMFILES(X86)", "C:/Program Files (x86)")) / "Steam" / "steamapps" / "common"
    if steam.exists():
        for parent in steam.parents:
            mo2_candidate = parent / "Mod Organizer 2"
            if mo2_candidate not in common:
                common.append(mo2_candidate)

    for p in common:
        try:
            if p.exists() and (p / "ModOrganizer.exe").exists():
                candidates.append(p.resolve())
        except Exception:
            pass
    return list(dict.fromkeys(candidates))


def get_mo2_profiles(mo2_path: Path) -> list[str]:
    """Devuelve nombres de perfiles en esa instalación de MO2."""
    profiles_dir = mo2_path / "profiles"
    if not profiles_dir.exists():
        return []
    return [d.name for d in profiles_dir.iterdir() if d.is_dir() and (d / "modlist.txt").exists()]


def get_game_docs_path(game_path: Path) -> Path:
    """Documents/My Games/Skyrim Special Edition"""
    docs = Path(os.environ.get("USERPROFILE", "")) / "Documents" / "My Games" / "Skyrim Special Edition"
    return docs


def detect_fallout4_path() -> Optional[Path]:
    """Detecta Fallout 4 desde Registry o Steam."""
    subkeys = [
        r"SOFTWARE\WOW6432Node\Bethesda Softworks\Fallout4",
        r"SOFTWARE\Bethesda Softworks\Fallout4",
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\Steam App 377160",
    ]
    for subkey in subkeys:
        val = _get_reg_key(winreg.HKEY_LOCAL_MACHINE, subkey, "Installed Path")
        if not val:
            val = _get_reg_key(winreg.HKEY_LOCAL_MACHINE, subkey, "InstallLocation")
        if val and Path(val).exists():
            return Path(val).resolve()
    steam = Path(os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)")) / "Steam" / "steamapps" / "common" / "Fallout 4"
    if steam.exists() and (steam / "Fallout4.exe").exists():
        return steam.resolve()
    return None


def get_fallout4_docs_path() -> Path:
    """Documents/My Games/Fallout4"""
    return Path(os.environ.get("USERPROFILE", "")) / "Documents" / "My Games" / "Fallout4"
