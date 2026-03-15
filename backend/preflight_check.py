"""Checklist pre-juego: SKSE, Engine Fixes, 255 plugins, F4SE, Buffout, masters, etc."""

from pathlib import Path
from typing import Optional


def check_f4se(game_path: Path) -> tuple[bool, str]:
    """Verifica F4SE (Fallout 4 Script Extender)."""
    if not game_path or not game_path.exists():
        return False, "Ruta de juego no encontrada"
    if (game_path / "f4se_loader.exe").exists():
        for dll in game_path.glob("f4se_*.dll"):
            return True, f"F4SE encontrado ({dll.name})"
        return True, "F4SE instalado"
    return False, "F4SE no detectado"


def check_buffout4(mods: list[str]) -> tuple[bool, str]:
    """Buffout 4 para Fallout 4 (similar a Engine Fixes)."""
    lower = [m.lower() for m in mods]
    if any("buffout" in m or "buffout 4" in m for m in lower):
        return True, "Buffout 4 detectado"
    return False, "Buffout 4 no encontrado (recomendado para estabilidad)"


def check_skse(game_path: Path) -> tuple[bool, str]:
    """Verifica que SKSE esté instalado."""
    if not game_path or not game_path.exists():
        return False, "Ruta de juego no encontrada"
    if (game_path / "skse64_loader.exe").exists() or (game_path / "skse_loader.exe").exists():
        for dll in game_path.glob("skse64_*.dll"):
            return True, f"SKSE encontrado ({dll.name})"
        return True, "SKSE instalado"
    return False, "SKSE no detectado"


def check_engine_fixes(mods: list[str], mods_path: Path) -> tuple[bool, str]:
    """Busca Engine Fixes en la lista de mods."""
    lower = [m.lower() for m in mods]
    for name in ["engine fixes", "sse engine fixes", "skyrim engine fixes"]:
        if any(name in m for m in lower):
            return True, "Engine Fixes detectado"
    return False, "Engine Fixes no encontrado (recomendado para estabilidad)"


def check_plugin_limit(plugins: list[str]) -> tuple[bool, str]:
    """Límite 255 plugins (ESP+ESM, ESL no cuentan para el límite principal)."""
    esp_esm = [p for p in plugins if p.lower().endswith((".esp", ".esm"))]
    n = len(esp_esm)
    if n > 255:
        return False, f"⚠️ {n} plugins ESP/ESM (límite 255) — reduce o convierte a ESL"
    if n > 245:
        return True, f"⚠️ {n}/255 plugins — cerca del límite"
    return True, f"✓ {n}/255 plugins"


def check_address_library(mods: list[str]) -> tuple[bool, str]:
    """Address Library requerido por muchos SKSE plugins."""
    lower = [m.lower() for m in mods]
    if any("address library" in m or "addresslibrary" in m for m in lower):
        return True, "Address Library detectado"
    return False, "Address Library no encontrado (muchos SKSE plugins lo requieren)"


def check_missing_masters(
    plugins: list[str],
    game_path: Optional[Path],
    mo2_path: Optional[Path],
) -> tuple[bool, str]:
    """Detecta plugins con masters faltantes."""
    if not plugins or not (game_path or mo2_path):
        return True, "—"
    try:
        from .missing_masters import find_missing_masters
        missing = find_missing_masters(plugins, game_path, mo2_path)
    except Exception:
        return True, "—"
    if not missing:
        return True, "✓ Sin masters faltantes"
    lines = [f"{m['plugin']} → {', '.join(m['missing_masters'])}" for m in missing[:5]]
    msg = f"⚠️ {len(missing)} plugin(s) con masters faltantes: " + "; ".join(lines)
    if len(missing) > 5:
        msg += f" (+{len(missing)-5} más)"
    return False, msg


def run_preflight(
    game_path: Optional[Path],
    mods: list[str],
    plugins: list[str],
    game_name: str = "Skyrim SE",
    mo2_path: Optional[Path] = None,
) -> list[dict]:
    """Ejecuta todos los checks según el juego. Devuelve lista de {ok, message, critical}."""
    results = []
    gp = game_path or Path()
    is_fo4 = "fallout" in game_name.lower() or "fo4" in game_name.lower()

    if is_fo4:
        ok, msg = check_f4se(gp)
        results.append({"ok": ok, "message": msg, "critical": True, "name": "F4SE"})
        ok, msg = check_buffout4(mods)
        results.append({"ok": ok, "message": msg, "critical": False, "name": "Buffout 4"})
    else:
        ok, msg = check_skse(gp)
        results.append({"ok": ok, "message": msg, "critical": True, "name": "SKSE"})
        ok, msg = check_engine_fixes(mods, Path())
        results.append({"ok": ok, "message": msg, "critical": False, "name": "Engine Fixes"})
        ok, msg = check_address_library(mods)
        results.append({"ok": ok, "message": msg, "critical": False, "name": "Address Library"})

    ok, msg = check_plugin_limit(plugins)
    results.append({"ok": ok, "message": msg, "critical": not ok, "name": "Límite 255"})
    ok, msg = check_missing_masters(plugins, gp if gp.exists() else None, mo2_path)
    results.append({"ok": ok, "message": msg, "critical": not ok, "name": "Masters"})
    return results
