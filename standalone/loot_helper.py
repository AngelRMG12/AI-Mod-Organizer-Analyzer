"""
Detecta y ejecuta LOOT.
"""

import os
import re
import shutil
from pathlib import Path
from typing import Optional

LOOT_DOWNLOAD_URL = "https://github.com/loot/loot/releases/latest"


def detect_loot(mo2_path: Optional[Path] = None) -> Optional[Path]:
    """
    Busca LOOT.exe en PATH, ubicaciones comunes, y dentro de MO2.
    """
    # PATH
    loot_exe = shutil.which("loot.exe") or shutil.which("LOOT.exe")
    if loot_exe:
        return Path(loot_exe).resolve()

    candidates = [
        Path("C:/Program Files/LOOT/LOOT.exe"),
        Path("C:/Program Files (x86)/LOOT/LOOT.exe"),
        Path(os.environ.get("PROGRAMFILES", "C:\\Program Files")) / "LOOT" / "LOOT.exe",
        Path(os.environ.get("PROGRAMFILES(X86)", "C:\\Program Files (x86)")) / "LOOT" / "LOOT.exe",
        Path.home() / "AppData" / "Local" / "LOOT" / "LOOT.exe",
        Path.home() / "Downloads" / "LOOT" / "LOOT.exe",
    ]

    for p in candidates:
        if p.exists():
            return p.resolve()

    # Dentro de MO2: ModOrganizer.ini puede tener rutas de ejecutables
    if mo2_path and mo2_path.exists():
        ini_path = mo2_path / "ModOrganizer.ini"
        if ini_path.exists():
            try:
                content = ini_path.read_text(encoding="utf-8", errors="ignore")
                for match in re.finditer(r'[Bb]inary\s*=\s*(.+\.exe)', content):
                    exe = Path(match.group(1).strip().strip('"'))
                    if "loot" in exe.name.lower() and exe.exists():
                        return exe.resolve()
            except Exception:
                pass
        # MO2 suele tener LOOT como herramienta en /tools o cerca
        for sub in ["LOOT", "loot", "tools/LOOT", "tools/loot"]:
            cand = mo2_path / sub / "LOOT.exe"
            if cand.exists():
                return cand.resolve()
        cand = mo2_path / "LOOT.exe"
        if cand.exists():
            return cand.resolve()

    return None
