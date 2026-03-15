"""
Reader standalone: usa rutas seleccionadas por el usuario (MO2 profile o manual).
Carga el reader del plugin sin importar mobase (evita la cadena plugin->main->mobase).
"""

import importlib.util
from pathlib import Path
from typing import Optional

_ROOT = Path(__file__).resolve().parent.parent
_READER_PATH = _ROOT / "plugin" / "ai_conflict_analyzer" / "reader.py"
_spec = importlib.util.spec_from_file_location("_reader_mod", _READER_PATH)
_reader_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_reader_mod)
collect_environment = _reader_mod.collect_environment


def collect_from_mo2(
    mo2_path: Path,
    profile_name: str,
    game_path: Optional[Path] = None,
    game_docs_path: Optional[Path] = None,
    include_file_conflicts: bool = True,
) -> dict:
    """
    Recopila todo el entorno desde un perfil de MO2.
    """
    profile_path = mo2_path / "profiles" / profile_name
    if not profile_path.exists():
        raise FileNotFoundError(f"No existe el perfil: {profile_path}")

    return collect_environment(
        profile_path=profile_path,
        mo2_base_path=mo2_path,
        game_path=game_path,
        game_docs_path=game_docs_path,
        include_file_conflicts=include_file_conflicts,
    )
