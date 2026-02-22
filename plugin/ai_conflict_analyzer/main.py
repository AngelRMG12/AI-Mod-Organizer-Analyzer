"""
AI Conflict Analyzer - Mod Organizer 2 Plugin
Reads your full MO2 environment (mods, plugins, file conflicts, Skyrim version,
Papyrus logs, SKSE logs) and uses AI + real-time web search to diagnose bugs.
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
        QMessageBox, QCheckBox, QGroupBox, QComboBox,
    )
    from PyQt5.QtCore import Qt, QThread, pyqtSignal
    from PyQt5.QtGui import QFont, QIcon
    MO2_ENV = True
except ImportError:
    MO2_ENV = False

from .reader import collect_environment

PLUGIN_VERSION = "0.2.0"
BACKEND_URL = os.environ.get("ACA_BACKEND_URL", "http://localhost:8000")


# --------------------------------------------------------------------------- #
# Worker thread                                                                 #
# --------------------------------------------------------------------------- #

if MO2_ENV:
    class AnalysisWorker(QThread):
        finished = pyqtSignal(dict)
        error = pyqtSignal(str)
        status = pyqtSignal(str)

        def __init__(self, env_data: dict, bug: str, language: str = "auto"):
            super().__init__()
            self.env_data = env_data
            self.bug = bug
            self.language = language

        def run(self):
            try:
                self.status.emit("Recolectando datos del entorno...")

                payload = {
                    "mods": self.env_data.get("mods", []),
                    "plugins": self.env_data.get("plugins", []),
                    "load_order": self.env_data.get("load_order", []),
                    "bug_description": self.bug,
                    "file_conflicts": self.env_data.get("file_conflicts", []),
                    "overwrite_files": self.env_data.get("overwrite_files", []),
                    "mod_metadata": self.env_data.get("mod_metadata", []),
                    "skyrim_version": self.env_data.get("skyrim_version"),
                    "skse_version": self.env_data.get("skse_version"),
                    "papyrus_errors": self.env_data.get("papyrus_errors", []),
                    "skse_errors": self.env_data.get("skse_errors", []),
                    "response_language": self.language,
                }

                self.status.emit("Buscando en Reddit y Nexus Mods...")
                resp = requests.post(
                    f"{BACKEND_URL}/analyze",
                    json=payload,
                    timeout=60,
                )
                resp.raise_for_status()
                self.finished.emit(resp.json())

            except requests.exceptions.ConnectionError:
                self.error.emit(
                    "No se pudo conectar al backend.\n"
                    f"¿Está corriendo en {BACKEND_URL}?\n\n"
                    "Corre: py run_backend.py"
                )
            except Exception as exc:
                self.error.emit(str(exc))


# --------------------------------------------------------------------------- #
# Dialog UI                                                                     #
# --------------------------------------------------------------------------- #

    class ConflictAnalyzerDialog(QDialog):
        def __init__(self, organizer, parent=None):
            super().__init__(parent)
            self.organizer = organizer
            self._env_data = {}
            self._build_ui()
            self._load_environment()

        def _build_ui(self):
            self.setWindowTitle(f"AI Conflict Analyzer v{PLUGIN_VERSION}")
            self.setMinimumSize(780, 600)
            self.setStyleSheet("""
                QDialog { background: #1e1e2e; color: #cdd6f4; font-family: Segoe UI; }
                QLabel  { color: #cdd6f4; }
                QGroupBox { color: #89b4fa; border: 1px solid #45475a; border-radius: 6px; padding: 8px; margin-top: 6px; }
                QGroupBox::title { subcontrol-origin: margin; left: 10px; }
                QTextEdit, QTextBrowser {
                    background: #181825; color: #cdd6f4;
                    border: 1px solid #45475a; border-radius: 6px;
                    padding: 6px; font-size: 13px;
                }
                QCheckBox { color: #cdd6f4; }
                QPushButton {
                    background: #89b4fa; color: #1e1e2e; font-weight: bold;
                    border-radius: 6px; padding: 8px 18px;
                }
                QPushButton:hover { background: #74c7ec; }
                QPushButton:disabled { background: #45475a; color: #6c7086; }
                QProgressBar {
                    border: 1px solid #45475a; border-radius: 4px;
                    background: #181825; height: 8px;
                }
                QProgressBar::chunk { background: #89b4fa; border-radius: 4px; }
            """)

            layout = QVBoxLayout(self)
            layout.setContentsMargins(20, 20, 20, 20)
            layout.setSpacing(10)

            title = QLabel(f"🔍 AI Conflict Analyzer")
            title.setFont(QFont("Segoe UI", 16, QFont.Bold))
            layout.addWidget(title)

            # Environment summary
            self.env_label = QLabel("Cargando entorno...")
            self.env_label.setWordWrap(True)
            self.env_label.setStyleSheet("color: #a6e3a1; font-size: 12px;")
            layout.addWidget(self.env_label)

            # Options
            opts = QGroupBox("Opciones de análisis")
            opts_layout = QHBoxLayout(opts)
            self.chk_file_conflicts = QCheckBox("Conflictos de archivos")
            self.chk_file_conflicts.setChecked(True)
            self.chk_papyrus = QCheckBox("Logs Papyrus/SKSE")
            self.chk_papyrus.setChecked(True)
            self.chk_web = QCheckBox("Reddit/Nexus en tiempo real")
            self.chk_web.setChecked(True)

            lang_label = QLabel("Idioma respuesta:")
            lang_label.setStyleSheet("color: #a6adc8; font-size: 12px;")
            self.lang_combo = QComboBox()
            self.lang_combo.setStyleSheet(
                "background: #313244; color: #cdd6f4; border: 1px solid #45475a; "
                "border-radius: 4px; padding: 3px 8px;"
            )
            self.lang_combo.addItems([
                "🌐 Auto (mismo idioma que el bug)",
                "🇲🇽 Español",
                "🇺🇸 English",
                "🇫🇷 Français",
                "🇩🇪 Deutsch",
                "🇧🇷 Português",
                "🇯🇵 日本語",
            ])
            opts_layout.addWidget(self.chk_file_conflicts)
            opts_layout.addWidget(self.chk_papyrus)
            opts_layout.addWidget(self.chk_web)
            opts_layout.addStretch()
            opts_layout.addWidget(lang_label)
            opts_layout.addWidget(self.lang_combo)
            layout.addWidget(opts)

            # Bug input
            self.bug_input = QTextEdit()
            self.bug_input.setPlaceholderText(
                "Describe el bug... Ej: NPCs con cara negra / T-pose / CTD al entrar a Whiterun / "
                "la interfaz de SkyUI no carga / animaciones rotas..."
            )
            self.bug_input.setMaximumHeight(90)
            layout.addWidget(self.bug_input)

            btn_row = QHBoxLayout()
            self.analyze_btn = QPushButton("Analizar")
            self.analyze_btn.clicked.connect(self._run_analysis)
            self.reload_btn = QPushButton("↺ Recargar entorno")
            self.reload_btn.clicked.connect(self._load_environment)
            self.reload_btn.setStyleSheet(
                "background: #45475a; color: #cdd6f4; font-weight: normal;"
            )
            btn_row.addWidget(self.analyze_btn)
            btn_row.addWidget(self.reload_btn)
            btn_row.addStretch()
            layout.addLayout(btn_row)

            self.status_label = QLabel("")
            self.status_label.setStyleSheet("color: #f9e2af; font-size: 12px;")
            layout.addWidget(self.status_label)

            self.progress = QProgressBar()
            self.progress.setRange(0, 0)
            self.progress.hide()
            layout.addWidget(self.progress)

            self.results = QTextBrowser()
            self.results.setOpenExternalLinks(True)
            layout.addWidget(self.results)

        def _load_environment(self):
            try:
                profile = self.organizer.profile()
                profile_path = Path(profile.absolutePath())
                mo2_base = Path(self.organizer.basePath())
                game_path = Path(self.organizer.managedGame().gameDirectory().absolutePath())
                game_docs = Path(self.organizer.managedGame().documentsDirectory().absolutePath())

                self._env_data = collect_environment(
                    profile_path=profile_path,
                    mo2_base_path=mo2_base,
                    game_path=game_path,
                    game_docs_path=game_docs,
                    include_file_conflicts=self.chk_file_conflicts.isChecked(),
                )

                mods_count = len(self._env_data.get("mods", []))
                plugins_count = len(self._env_data.get("plugins", []))
                conflicts_count = len(self._env_data.get("file_conflicts", []))
                overwrite_count = len(self._env_data.get("overwrite_files", []))
                papyrus_count = len(self._env_data.get("papyrus_errors", []))
                sky_ver = self._env_data.get("skyrim_version") or "no detectada"
                skse_ver = self._env_data.get("skse_version") or "no detectado"

                self.env_label.setText(
                    f"✅ {mods_count} mods activos · {plugins_count} plugins · "
                    f"{conflicts_count} conflictos de archivos · {overwrite_count} en overwrite · "
                    f"{papyrus_count} errores Papyrus · {sky_ver} · {skse_ver}"
                )
            except Exception as exc:
                self.env_label.setText(f"⚠️ Error cargando entorno: {exc}")
                self.env_label.setStyleSheet("color: #f38ba8; font-size: 12px;")

        def _run_analysis(self):
            bug = self.bug_input.toPlainText().strip()
            if not bug:
                QMessageBox.warning(self, "Falta descripción", "Describe el bug antes de analizar.")
                return
            if not self._env_data.get("mods"):
                QMessageBox.warning(self, "Sin datos", "No se pudo leer el entorno de MO2. Recarga primero.")
                return

            env_data = dict(self._env_data)
            if not self.chk_papyrus.isChecked():
                env_data["papyrus_errors"] = []
                env_data["skse_errors"] = []
            if not self.chk_file_conflicts.isChecked():
                env_data["file_conflicts"] = []

            # Map combo selection to language code
            lang_map = {
                0: "auto", 1: "Spanish", 2: "English",
                3: "French", 4: "German", 5: "Portuguese", 6: "Japanese",
            }
            language = lang_map.get(self.lang_combo.currentIndex(), "auto")

            self.analyze_btn.setEnabled(False)
            self.progress.show()
            self.results.setPlainText("Analizando...")

            self._worker = AnalysisWorker(env_data, bug, language)
            self._worker.status.connect(self._on_status)
            self._worker.finished.connect(self._on_finished)
            self._worker.error.connect(self._on_error)
            self._worker.start()

        def _on_status(self, msg: str):
            self.status_label.setText(msg)

        def _on_finished(self, result: dict):
            self.progress.hide()
            self.status_label.setText("")
            self.analyze_btn.setEnabled(True)
            self.results.setHtml(self._format_results(result))

        def _on_error(self, msg: str):
            self.progress.hide()
            self.status_label.setText("")
            self.analyze_btn.setEnabled(True)
            self.results.setPlainText(f"Error:\n{msg}")

        @staticmethod
        def _format_results(result: dict) -> str:
            html = "<style>body{font-family:Segoe UI;color:#cdd6f4;background:#181825;line-height:1.5}</style>"

            suspects = result.get("suspects", [])
            explanation = result.get("explanation", "")
            web_sources = result.get("web_sources", [])

            if not suspects and not explanation:
                html += "<p>No se encontraron conflictos. Intenta con una descripción más detallada.</p>"
                return html

            if suspects:
                html += "<h3 style='color:#a6e3a1'>🎯 Mods sospechosos</h3><ul>"
                for s in suspects:
                    pct = int(s["confidence"] * 100)
                    color = "#a6e3a1" if pct >= 70 else "#f9e2af" if pct >= 40 else "#cdd6f4"
                    html += (
                        f"<li style='margin-bottom:10px'>"
                        f"<b style='color:#89b4fa;font-size:14px'>{s['mod']}</b> "
                        f"<span style='color:{color}'>{pct}% probabilidad</span><br>"
                        f"<small style='color:#bac2de'>{s.get('reason', '')}</small><br>"
                        f"<small style='color:#f9e2af'>💡 {s.get('fix', '')}</small>"
                        f"</li>"
                    )
                html += "</ul>"

            if explanation:
                clean = explanation.replace("\n", "<br>")
                # Remove the raw JSON block from display
                import re
                clean = re.sub(r"```json.*?```", "", clean, flags=re.DOTALL)
                html += f"<h3 style='color:#cba6f7'>📝 Análisis completo</h3><p>{clean}</p>"

            if web_sources:
                html += "<h3 style='color:#74c7ec'>🌐 Fuentes consultadas</h3><ul>"
                for url in web_sources:
                    html += f"<li><a href='{url}' style='color:#89b4fa'>{url}</a></li>"
                html += "</ul>"

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
            return "Full-environment AI conflict analysis with real-time web search."

        def version(self) -> mobase.VersionInfo:
            return mobase.VersionInfo(0, 2, 0, mobase.ReleaseType.FINAL)

        def isActive(self) -> bool:
            return True

        def settings(self) -> list:
            return []

        def displayName(self) -> str:
            return "AI Conflict Analyzer"

        def tooltip(self) -> str:
            return "Analyze your full mod environment with AI + real-time web search"

        def icon(self) -> QIcon:
            return QIcon()

        def display(self) -> None:
            dialog = ConflictAnalyzerDialog(self._organizer)
            dialog.exec_()


    def createPlugin() -> mobase.IPlugin:
        return AIConflictAnalyzerPlugin()
