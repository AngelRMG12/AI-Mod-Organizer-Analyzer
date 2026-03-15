"""
Detecta plugins con masters faltantes (dependencias no satisfechas).
Lee el header TES4 de archivos ESP/ESM para extraer la lista de masters.
"""

from pathlib import Path
from typing import Optional


def _find_plugin_path(plugin_name: str, search_paths: list[Path]) -> Optional[Path]:
    """Busca un plugin en game Data/ o en carpetas de mods."""
    name = plugin_name.strip().replace("*", "")
    for base in search_paths:
        if not base.exists():
            continue
        # Directo en Data/ o en raíz del mod
        for candidate in [base / name, base / "Data" / name]:
            if candidate.exists():
                return candidate
        # mods/ModName/ puede tener Data/ o archivos en raíz
        if base.name == "mods":
            for mod_dir in base.iterdir():
                if mod_dir.is_dir():
                    for sub in [mod_dir / name, mod_dir / "Data" / name]:
                        if sub.exists():
                            return sub
    return None


def _read_masters_from_plugin(filepath: Path) -> list[str]:
    """
    Lee los masters de un plugin TES4 (Skyrim/FO4).
    Formato: TES4 header con subrecords MAST (nombre null-terminated).
    """
    masters = []
    try:
        data = filepath.read_bytes()[:8192]
    except Exception:
        return []
    if len(data) < 24:
        return []
    if data[0:4] != b"TES4":
        return []
    # Saltar record header: 4 (TES4) + 4 (size) + 4 (flags) = 12
    pos = 12
    while pos + 8 <= len(data):
        sub_type = data[pos : pos + 4].decode("latin-1", errors="ignore")
        sub_size = int.from_bytes(data[pos + 4 : pos + 8], "little")
        pos += 8
        if pos + sub_size > len(data):
            break
        if sub_type == "MAST":
            name = data[pos : pos + sub_size].split(b"\x00")[0].decode("latin-1", errors="ignore").strip()
            if name.lower().endswith((".esm", ".esp", ".esl")) and name not in masters:
                masters.append(name)
        # DATA sigue a MAST pero no nos interesa
        pos += sub_size
    return masters


def find_missing_masters(
    plugins_in_load_order: list[str],
    game_path: Optional[Path] = None,
    mo2_path: Optional[Path] = None,
) -> list[dict]:
    """
    Detecta plugins que requieren masters que no están en load_order.

    plugins_in_load_order: lista ordenada de plugins cargados.
    game_path: ruta raíz del juego (busca en game_path/Data/).
    mo2_path: ruta raíz de MO2 (busca en mo2_path/mods/).

    Returns: [{plugin, missing_masters: [...]}, ...]
    """
    active = {p.strip().lower().replace("*", ""): p for p in plugins_in_load_order}
    seen_plugins = set()
    results = []
    search_paths = []
    if game_path and (game_path / "Data").exists():
        search_paths.append(game_path / "Data")
    if mo2_path and (mo2_path / "mods").exists():
        search_paths.append(mo2_path / "mods")
    if not search_paths:
        return []

    for plug in plugins_in_load_order:
        name = plug.strip().replace("*", "").lower()
        if not name.endswith((".esp", ".esm", ".esl")):
            continue
        plug_path = _find_plugin_path(name, search_paths)
        if not plug_path or not plug_path.exists():
            continue
        masters = _read_masters_from_plugin(plug_path)
        if not masters:
            continue
        missing = []
        for m in masters:
            m_lower = m.lower()
            if m_lower not in active and m_lower not in seen_plugins:
                missing.append(m)
        if missing:
            results.append({"plugin": plug, "missing_masters": missing})
        seen_plugins.add(name)

    return results
