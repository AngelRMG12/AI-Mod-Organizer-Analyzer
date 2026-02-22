import os
import json
import urllib.request
import urllib.error
from pathlib import Path

import mobase
try:
    from PyQt6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel,
        QTextEdit, QPushButton, QTextBrowser, QProgressBar,
        QMessageBox, QCheckBox, QGroupBox, QComboBox,
    )
    from PyQt6.QtCore import QThread, pyqtSignal
    from PyQt6.QtGui import QFont, QIcon
except ImportError:
    from PyQt5.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QLabel,
        QTextEdit, QPushButton, QTextBrowser, QProgressBar,
        QMessageBox, QCheckBox, QGroupBox, QComboBox,
    )
    from PyQt5.QtCore import QThread, pyqtSignal
    from PyQt5.QtGui import QFont, QIcon

from .reader import collect_environment

PLUGIN_VERSION = "0.2.0"
BACKEND_URL = os.environ.get("ACA_BACKEND_URL", "http://localhost:8000")

STYLE = """
QDialog { background: #1e1e2e; color: #cdd6f4; font-family: Segoe UI; }
QLabel  { color: #cdd6f4; }
QGroupBox {
    color: #89b4fa; border: 1px solid #45475a;
    border-radius: 6px; padding: 8px; margin-top: 6px;
}
QGroupBox::title { subcontrol-origin: margin; left: 10px; }
QTextEdit, QTextBrowser {
    background: #181825; color: #cdd6f4;
    border: 1px solid #45475a; border-radius: 6px;
    padding: 6px; font-size: 13px;
}
QCheckBox { color: #cdd6f4; spacing: 6px; }
QComboBox {
    background: #313244; color: #cdd6f4;
    border: 1px solid #45475a; border-radius: 4px; padding: 3px 8px;
}
QPushButton {
    background: #89b4fa; color: #1e1e2e; font-weight: bold;
    border-radius: 6px; padding: 8px 18px; border: none;
}
QPushButton:hover { background: #74c7ec; }
QPushButton:disabled { background: #45475a; color: #6c7086; }
QPushButton#secondary {
    background: #45475a; color: #cdd6f4; font-weight: normal;
}
QProgressBar {
    border: 1px solid #45475a; border-radius: 4px;
    background: #181825; height: 8px;
}
QProgressBar::chunk { background: #89b4fa; border-radius: 4px; }
"""

LANG_MAP = {
    0: "auto",
    1: "Spanish",
    2: "English",
    3: "French",
    4: "German",
    5: "Portuguese",
    6: "Japanese",
}


# --------------------------------------------------------------------------- #
# Worker thread (keeps UI responsive during network calls)                      #
# --------------------------------------------------------------------------- #

class AnalysisWorker(QThread):
    finished = pyqtSignal(dict)
    error    = pyqtSignal(str)
    status   = pyqtSignal(str)

    def __init__(self, payload: dict):
        super().__init__()
        self._payload = payload

    def run(self):
        try:
            self.status.emit("Buscando en Reddit y Nexus Mods...")
            body = json.dumps(self._payload).encode("utf-8")
            req = urllib.request.Request(
                f"{BACKEND_URL}/analyze",
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode("utf-8"))
            self.finished.emit(result)
        except urllib.error.URLError:
            self.error.emit(
                f"No se pudo conectar al backend en {BACKEND_URL}\n\n"
                "Asegúrate de que está corriendo:\n  py run_backend.py"
            )
        except Exception as exc:
            self.error.emit(str(exc))


# --------------------------------------------------------------------------- #
# Dialog UI                                                                     #
# --------------------------------------------------------------------------- #

class ConflictAnalyzerDialog(QDialog):
    def __init__(self, organizer, parent=None):
        super().__init__(parent)
        self._organizer = organizer
        self._env_data  = {}
        self._worker    = None
        self.setStyleSheet(STYLE)
        self._build_ui()
        self._load_env()

    def _build_ui(self):
        self.setWindowTitle(f"AI Conflict Analyzer  v{PLUGIN_VERSION}")
        self.setMinimumSize(800, 620)

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(10)

        # Title
        title = QLabel("🔍  AI Conflict Analyzer")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        root.addWidget(title)

        # Environment summary
        self.env_label = QLabel("Cargando entorno de MO2…")
        self.env_label.setWordWrap(True)
        self.env_label.setStyleSheet("color:#a6e3a1; font-size:12px;")
        root.addWidget(self.env_label)

        # Options row
        opts = QGroupBox("Opciones")
        row  = QHBoxLayout(opts)

        self.chk_conflicts = QCheckBox("Conflictos de archivos")
        self.chk_conflicts.setChecked(True)
        self.chk_papyrus   = QCheckBox("Logs Papyrus / SKSE")
        self.chk_papyrus.setChecked(True)
        self.chk_web       = QCheckBox("Reddit / Nexus tiempo real")
        self.chk_web.setChecked(True)

        row.addWidget(self.chk_conflicts)
        row.addWidget(self.chk_papyrus)
        row.addWidget(self.chk_web)
        row.addStretch()

        row.addWidget(QLabel("Idioma:"))
        self.lang_combo = QComboBox()
        self.lang_combo.addItems([
            "🌐 Auto",  "🇲🇽 Español", "🇺🇸 English",
            "🇫🇷 Français", "🇩🇪 Deutsch",
            "🇧🇷 Português", "🇯🇵 日本語",
        ])
        row.addWidget(self.lang_combo)
        root.addWidget(opts)

        # Bug description
        self.bug_input = QTextEdit()
        self.bug_input.setPlaceholderText(
            "Describe el bug…  Ej: NPCs cara negra · T-pose · "
            "CTD al entrar a Whiterun · SkyUI no carga · animaciones rotas"
        )
        self.bug_input.setMaximumHeight(90)
        root.addWidget(self.bug_input)

        # Buttons
        btns = QHBoxLayout()
        self.btn_analyze = QPushButton("Analizar")
        self.btn_analyze.clicked.connect(self._run)

        self.btn_reload = QPushButton("↺ Recargar entorno")
        self.btn_reload.setObjectName("secondary")
        self.btn_reload.clicked.connect(self._load_env)

        btns.addWidget(self.btn_analyze)
        btns.addWidget(self.btn_reload)
        btns.addStretch()
        root.addLayout(btns)

        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("color:#f9e2af; font-size:12px;")
        root.addWidget(self.lbl_status)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        root.addWidget(self.progress)

        self.results = QTextBrowser()
        self.results.setOpenExternalLinks(True)
        root.addWidget(self.results)

    # ------------------------------------------------------------------ env --

    def _load_env(self):
        try:
            profile    = self._organizer.profile()
            profile_path = Path(profile.absolutePath())
            mo2_base   = Path(self._organizer.basePath())
            game_path  = Path(self._organizer.managedGame().gameDirectory().absolutePath())
            game_docs  = Path(self._organizer.managedGame().documentsDirectory().absolutePath())

            self._env_data = collect_environment(
                profile_path=profile_path,
                mo2_base_path=mo2_base,
                game_path=game_path,
                game_docs_path=game_docs,
                include_file_conflicts=self.chk_conflicts.isChecked(),
            )

            n_mods      = len(self._env_data.get("mods", []))
            n_plugins   = len(self._env_data.get("plugins", []))
            n_conflicts = len(self._env_data.get("file_conflicts", []))
            n_overwrite = len(self._env_data.get("overwrite_files", []))
            n_papyrus   = len(self._env_data.get("papyrus_errors", []))
            sky_ver     = self._env_data.get("skyrim_version") or "versión no detectada"
            skse_ver    = self._env_data.get("skse_version")   or "SKSE no detectado"

            self.env_label.setText(
                f"✅  {n_mods} mods · {n_plugins} plugins · "
                f"{n_conflicts} conflictos de archivos · {n_overwrite} en overwrite · "
                f"{n_papyrus} errores Papyrus · {sky_ver} · {skse_ver}"
            )
            self.env_label.setStyleSheet("color:#a6e3a1; font-size:12px;")
        except Exception as exc:
            self.env_label.setText(f"⚠️  Error cargando entorno: {exc}")
            self.env_label.setStyleSheet("color:#f38ba8; font-size:12px;")

    # --------------------------------------------------------------- analyze --

    def _run(self):
        bug = self.bug_input.toPlainText().strip()
        if not bug:
            QMessageBox.warning(self, "Sin descripción", "Escribe el bug antes de analizar.")
            return

        env = dict(self._env_data)
        if not self.chk_papyrus.isChecked():
            env["papyrus_errors"] = []
            env["skse_errors"]    = []
        if not self.chk_conflicts.isChecked():
            env["file_conflicts"] = []

        payload = {
            "mods":             env.get("mods", []),
            "plugins":          env.get("plugins", []),
            "load_order":       env.get("load_order", []),
            "bug_description":  bug,
            "file_conflicts":   env.get("file_conflicts", []),
            "overwrite_files":  env.get("overwrite_files", []),
            "mod_metadata":     env.get("mod_metadata", []),
            "skyrim_version":   env.get("skyrim_version"),
            "skse_version":     env.get("skse_version"),
            "papyrus_errors":   env.get("papyrus_errors", []),
            "skse_errors":      env.get("skse_errors", []),
            "response_language": LANG_MAP.get(self.lang_combo.currentIndex(), "auto"),
        }

        self.btn_analyze.setEnabled(False)
        self.progress.show()
        self.results.clear()

        self._worker = AnalysisWorker(payload)
        self._worker.status.connect(self.lbl_status.setText)
        self._worker.finished.connect(self._on_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_done(self, result: dict):
        self.progress.hide()
        self.btn_analyze.setEnabled(True)
        self.lbl_status.setText("")
        self.results.setHtml(_format(result))

    def _on_error(self, msg: str):
        self.progress.hide()
        self.btn_analyze.setEnabled(True)
        self.lbl_status.setText("")
        self.results.setPlainText(f"Error:\n{msg}")


# --------------------------------------------------------------------------- #
# HTML formatter                                                                #
# --------------------------------------------------------------------------- #

def _format(result: dict) -> str:
    import re
    html = "<style>body{font-family:Segoe UI;color:#cdd6f4;background:#181825;line-height:1.5}</style>"

    suspects    = result.get("suspects", [])
    explanation = result.get("explanation", "")
    sources     = result.get("web_sources", [])

    if suspects:
        html += "<h3 style='color:#a6e3a1'>🎯 Mods sospechosos</h3><ul>"
        for s in suspects:
            pct   = int(s["confidence"] * 100)
            color = "#a6e3a1" if pct >= 70 else "#f9e2af" if pct >= 40 else "#cdd6f4"
            html += (
                f"<li style='margin-bottom:10px'>"
                f"<b style='color:#89b4fa;font-size:14px'>{s['mod']}</b> "
                f"<span style='color:{color}'>{pct}%</span><br>"
                f"<small style='color:#bac2de'>{s.get('reason','')}</small><br>"
                f"<small style='color:#f9e2af'>💡 {s.get('fix','')}</small>"
                f"</li>"
            )
        html += "</ul>"

    if explanation:
        clean = re.sub(r"```json.*?```", "", explanation, flags=re.DOTALL)
        clean = clean.replace("\n", "<br>")
        html += f"<h3 style='color:#cba6f7'>📝 Análisis</h3><p>{clean}</p>"

    if sources:
        html += "<h3 style='color:#74c7ec'>🌐 Fuentes</h3><ul>"
        for url in sources:
            html += f"<li><a href='{url}' style='color:#89b4fa'>{url}</a></li>"
        html += "</ul>"

    if not suspects and not explanation:
        html += "<p>Sin resultados. Intenta con una descripción más detallada.</p>"

    return html


# --------------------------------------------------------------------------- #
# MO2 plugin registration — createPlugin MUST be at module level               #
# --------------------------------------------------------------------------- #

class AIConflictAnalyzerPlugin(mobase.IPluginTool):

    def __init__(self):
        super().__init__()
        self._organizer = None

    def init(self, organizer: mobase.IOrganizer) -> bool:
        self._organizer = organizer
        return True

    def name(self)        -> str: return "AI Conflict Analyzer"
    def author(self)      -> str: return "AngelRMG12"
    def description(self) -> str: return "AI-powered mod conflict analysis with real-time web search."
    def isActive(self)    -> bool: return True
    def settings(self)    -> list: return []
    def displayName(self) -> str: return "AI Conflict Analyzer"
    def tooltip(self)     -> str: return "Analyze mod conflicts with AI + Reddit/Nexus search"
    def icon(self)        -> QIcon: return QIcon()

    def version(self) -> mobase.VersionInfo:
        return mobase.VersionInfo(0, 2, 0, mobase.ReleaseType.FINAL)

    def display(self) -> None:
        dlg = ConflictAnalyzerDialog(self._organizer)
        dlg.exec_()


def createPlugin() -> mobase.IPlugin:
    return AIConflictAnalyzerPlugin()
