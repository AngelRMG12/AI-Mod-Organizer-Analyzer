"""
MO2 profile reader utilities.
Reads modlist.txt, plugins.txt, loadorder.txt, and overwrite conflicts.
"""

from pathlib import Path


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
    """Returns the exact load order from loadorder.txt."""
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


def find_overwrite_conflicts(mo2_base_path: Path) -> list[dict]:
    """
    Scans the MO2 overwrite folder and returns a list of conflicting files
    with their relative paths.
    """
    overwrite_dir = mo2_base_path / "overwrite"
    conflicts = []
    if not overwrite_dir.exists():
        return conflicts
    for file in overwrite_dir.rglob("*"):
        if file.is_file():
            conflicts.append({
                "file": str(file.relative_to(overwrite_dir)),
                "full_path": str(file),
            })
    return conflicts
