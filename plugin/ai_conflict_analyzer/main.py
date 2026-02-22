"""
AI Conflict Analyzer - Mod Organizer 2 Plugin
Reads your load order and mod list, then uses AI to diagnose what mods
may be causing a specific bug you describe.
"""

import os
import sys
import json
import requests
from pathlib import Path

try:
    import mobase
    from PyQt5.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel,
        QTextEdit, QPushButton, QTextBrowser, QProgressBar,
        QMessageBox, QSizePolicy
    )
    from PyQt5.QtCore import Qt, QThread, pyqtSignal
    from PyQt5.QtGui import QFont, QIcon
    MO2_ENV = True
except ImportError:
    MO2_ENV = False

# --------------------------------------------------------------------------- #
# Config                                                                        #
# --------------------------------------------------------------------------- #
PLUGIN_VERSION = "0.1.0"
BACKEND_URL = os.environ.get("ACA_BACKEND_URL", "http://localhost:8000")
KNOWLEDGE_BASE_PATH = Path(__file__).parent.parent.parent / "knowledge_base" / "conflicts.json"


# --------------------------------------------------------------------------- #
# Utilities                                                                     #
# --------------------------------------------------------------------------- #

def load_knowledge_base() -> dict:
    if KNOWLEDGE_BASE_PATH.exists():
        with open(KNOWLEDGE_BASE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def get_mo2_profile_path(organizer) -> Path:
    profile = organizer.profile()
    return Path(profile.absolutePath())


def read_modlist(profile_path: Path) -> list[str]:
    modlist_file = profile_path / "modlist.txt"
    mods = []
    if modlist_file.exists():
        with open(modlist_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("+"):
                    mods.append(line[1:].strip())
    return mods


def read_plugins(profile_path: Path) -> list[str]:
    plugins_file = profile_path / "plugins.txt"
    plugins = []
    if plugins_file.exists():
        with open(plugins_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("*"):
                    plugins.append(line[1:].strip())
                elif line and not line.startswith("#"):
                    plugins.append(line)
    return plugins


def local_heuristic_search(mods: list[str], bug_description: str, kb: dict) -> list[dict]:
    """
    Fast offline pass: checks bug description keywords against the
    knowledge base and returns matching mods with a confidence score.
    """
    suspects = []
    bug_lower = bug_description.lower()

    for bug_key, conflict_info in kb.items():
        if bug_key.lower() in bug_lower:
            keywords = conflict_info.get("keywords", [])
            related_mods = conflict_info.get("mods", [])
            fix = conflict_info.get("fix", "No fix available in local knowledge base.")
            for mod in mods:
                for keyword in related_mods:
                    if keyword.lower() in mod.lower():
                        suspects.append({
                            "mod": mod,
                            "confidence": conflict_info.get("confidence", 0.6),
                            "reason": f"Known conflict with '{bug_key}'",
                            "fix": fix,
                        })
    return suspects


def call_backend(mods: list[str], plugins: list[str], bug: str) -> dict:
    """
    Calls the FastAPI backend which uses an LLM to perform a deeper analysis.
    Falls back gracefully if the backend is unreachable.
    """
    payload = {
        "mods": mods,
        "plugins": plugins,
        "bug_description": bug,
    }
    try:
        resp = requests.post(f"{BACKEND_URL}/analyze", json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        return {"error": str(exc), "suspects": [], "explanation": ""}


# --------------------------------------------------------------------------- #
# Worker thread (keeps UI responsive)                                           #
# --------------------------------------------------------------------------- #

if MO2_ENV:
    class AnalysisWorker(QThread):
        finished = pyqtSignal(dict)
        error = pyqtSignal(str)

        def __init__(self, mods, plugins, bug, kb):
            super().__init__()
            self.mods = mods
            self.plugins = plugins
            self.bug = bug
            self.kb = kb

        def run(self):
            try:
                local_suspects = local_heuristic_search(self.mods, self.bug, self.kb)
                backend_result = call_backend(self.mods, self.plugins, self.bug)

                result = {
                    "local_suspects": local_suspects,
                    "ai_suspects": backend_result.get("suspects", []),
                    "explanation": backend_result.get("explanation", ""),
                    "backend_error": backend_result.get("error"),
                }
                self.finished.emit(result)
            except Exception as exc:
                self.error.emit(str(exc))


# --------------------------------------------------------------------------- #
# Dialog UI                                                                     #
# --------------------------------------------------------------------------- #

    class ConflictAnalyzerDialog(QDialog):
        def __init__(self, organizer, parent=None):
            super().__init__(parent)
            self.organizer = organizer
            self.kb = load_knowledge_base()
            self._build_ui()

        def _build_ui(self):
            self.setWindowTitle("AI Conflict Analyzer")
            self.setMinimumSize(700, 520)
            self.setStyleSheet("""
                QDialog { background: #1e1e2e; color: #cdd6f4; font-family: Segoe UI; }
                QLabel  { color: #cdd6f4; }
                QTextEdit, QTextBrowser {
                    background: #181825; color: #cdd6f4;
                    border: 1px solid #45475a; border-radius: 6px;
                    padding: 6px; font-size: 13px;
                }
                QPushButton {
                    background: #89b4fa; color: #1e1e2e; font-weight: bold;
                    border-radius: 6px; padding: 8px 18px;
                }
                QPushButton:hover { background: #74c7ec; }
                QPushButton:disabled { background: #45475a; color: #6c7086; }
                QProgressBar {
                    border: 1px solid #45475a; border-radius: 4px;
                    background: #181825; height: 8px; text-align: center;
                }
                QProgressBar::chunk { background: #89b4fa; border-radius: 4px; }
            """)

            layout = QVBoxLayout(self)
            layout.setContentsMargins(20, 20, 20, 20)
            layout.setSpacing(12)

            title = QLabel("🔍 AI Conflict Analyzer")
            title.setFont(QFont("Segoe UI", 16, QFont.Bold))
            layout.addWidget(title)

            subtitle = QLabel("Describe tu bug y el analizador cruzará tu load order con la IA para encontrar el conflicto.")
            subtitle.setWordWrap(True)
            layout.addWidget(subtitle)

            self.bug_input = QTextEdit()
            self.bug_input.setPlaceholderText("Ej: Los NPCs tienen la cara negra / T-pose en animaciones / CTD al entrar a Whiterun...")
            self.bug_input.setMaximumHeight(100)
            layout.addWidget(self.bug_input)

            btn_row = QHBoxLayout()
            self.analyze_btn = QPushButton("Analizar")
            self.analyze_btn.clicked.connect(self._run_analysis)
            btn_row.addWidget(self.analyze_btn)
            btn_row.addStretch()
            layout.addLayout(btn_row)

            self.progress = QProgressBar()
            self.progress.setRange(0, 0)
            self.progress.hide()
            layout.addWidget(self.progress)

            self.results = QTextBrowser()
            self.results.setOpenExternalLinks(True)
            layout.addWidget(self.results)

        def _run_analysis(self):
            bug = self.bug_input.toPlainText().strip()
            if not bug:
                QMessageBox.warning(self, "Falta descripción", "Por favor describe el bug antes de analizar.")
                return

            profile_path = get_mo2_profile_path(self.organizer)
            mods = read_modlist(profile_path)
            plugins = read_plugins(profile_path)

            self.analyze_btn.setEnabled(False)
            self.progress.show()
            self.results.setPlainText("Analizando...")

            self._worker = AnalysisWorker(mods, plugins, bug, self.kb)
            self._worker.finished.connect(self._on_finished)
            self._worker.error.connect(self._on_error)
            self._worker.start()

        def _on_finished(self, result: dict):
            self.progress.hide()
            self.analyze_btn.setEnabled(True)
            self.results.setHtml(self._format_results(result))

        def _on_error(self, msg: str):
            self.progress.hide()
            self.analyze_btn.setEnabled(True)
            self.results.setPlainText(f"Error durante el análisis:\n{msg}")

        @staticmethod
        def _format_results(result: dict) -> str:
            html = "<style>body{font-family:Segoe UI;color:#cdd6f4;background:#181825;}</style>"

            if result.get("backend_error"):
                html += f"<p style='color:#f38ba8'>⚠️ Backend no disponible: {result['backend_error']}<br>Mostrando solo resultados locales.</p><hr>"

            local = result.get("local_suspects", [])
            ai_suspects = result.get("ai_suspects", [])
            explanation = result.get("explanation", "")

            if not local and not ai_suspects:
                html += "<p>No se encontraron conflictos conocidos. Intenta describir el bug con más detalle.</p>"
                return html

            if local:
                html += "<h3 style='color:#a6e3a1'>📦 Conflictos detectados (base local)</h3><ul>"
                for s in local:
                    pct = int(s['confidence'] * 100)
                    html += (
                        f"<li><b style='color:#89b4fa'>{s['mod']}</b> — "
                        f"<span style='color:#a6e3a1'>{pct}% probabilidad</span><br>"
                        f"<small>{s['reason']}</small><br>"
                        f"<small style='color:#f9e2af'>💡 {s['fix']}</small></li>"
                    )
                html += "</ul>"

            if ai_suspects:
                html += "<h3 style='color:#cba6f7'>🤖 Análisis IA</h3><ul>"
                for s in ai_suspects:
                    pct = int(s.get("confidence", 0) * 100)
                    html += (
                        f"<li><b style='color:#89b4fa'>{s.get('mod', 'Desconocido')}</b> — "
                        f"<span style='color:#a6e3a1'>{pct}%</span><br>"
                        f"<small>{s.get('reason', '')}</small></li>"
                    )
                html += "</ul>"

            if explanation:
                html += f"<h3 style='color:#f9e2af'>📝 Explicación</h3><p>{explanation}</p>"

            return html


# --------------------------------------------------------------------------- #
# MO2 plugin registration                                                       #
# --------------------------------------------------------------------------- #

    class AIConflictAnalyzerPlugin(mobase.IPluginTool):
        def __init__(self):
            super().__init__()
            self._organizer = None

        def init(self, organizer: mobase.IOrganizer) -> bool:
            self._organizer = organizer
            return True

        def name(self) -> str:
            return "AI Conflict Analyzer"

        def author(self) -> str:
            return "AngelRMG12"

        def description(self) -> str:
            return "Uses AI to identify which mods are likely causing your bug."

        def version(self) -> mobase.VersionInfo:
            return mobase.VersionInfo(0, 1, 0, mobase.ReleaseType.FINAL)

        def isActive(self) -> bool:
            return True

        def settings(self) -> list:
            return []

        def displayName(self) -> str:
            return "AI Conflict Analyzer"

        def tooltip(self) -> str:
            return "Analyze your mod list with AI to find conflict sources"

        def icon(self) -> QIcon:
            return QIcon()

        def display(self) -> None:
            dialog = ConflictAnalyzerDialog(self._organizer)
            dialog.exec_()


    def createPlugin() -> mobase.IPlugin:
        return AIConflictAnalyzerPlugin()
