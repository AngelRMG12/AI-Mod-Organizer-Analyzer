"""
AI Conflict Analyzer - Standalone App
Estilo BodySlide/Nemesis: análisis, load order, buenas prácticas, acciones útiles.
"""

import asyncio
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QTextEdit, QPushButton, QTextBrowser, QProgressBar,
        QMessageBox, QCheckBox, QGroupBox, QComboBox, QFileDialog,
        QTabWidget, QScrollArea, QFrame, QGridLayout,
        QDialog, QListWidget, QListWidgetItem, QPlainTextEdit,
    )
    from PyQt6.QtCore import QThread, pyqtSignal, Qt
    from PyQt6.QtGui import QFont, QCursor, QShortcut, QKeySequence
    PYQT = 6
except ImportError:
    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QTextEdit, QPushButton, QTextBrowser, QProgressBar,
        QMessageBox, QCheckBox, QGroupBox, QComboBox, QFileDialog,
        QTabWidget, QScrollArea, QFrame, QGridLayout,
        QDialog, QListWidget, QListWidgetItem, QPlainTextEdit, QShortcut,
    )
    from PyQt5.QtCore import QThread, pyqtSignal, Qt
    from PyQt5.QtGui import QFont, QCursor, QKeySequence
    PYQT = 5

try:
    USER_ROLE = Qt.ItemDataRole.UserRole
except AttributeError:
    USER_ROLE = Qt.UserRole
import json
from standalone.path_detector import (
    detect_skyrim_path,
    detect_fallout4_path,
    detect_mo2_paths,
    get_mo2_profiles,
    get_game_docs_path,
    get_fallout4_docs_path,
)
from standalone.standalone_reader import collect_from_mo2
from standalone.best_practices import BEST_PRACTICES, suggest_plugin_order
from standalone.bug_templates import BUG_TEMPLATES
from backend.preflight_check import run_preflight
from standalone.history import init_db, save_analysis, get_recent, clear_history
from standalone.loot_helper import detect_loot, LOOT_DOWNLOAD_URL

VERSION = "0.5.0"

STYLE_DARK = """
QMainWindow, QWidget { background: #0d0d14; color: #cdd6f4; }
QLabel { color: #cdd6f4; }
QTabWidget::pane {
    border: 1px solid #313244;
    border-radius: 10px;
    background: #11111b;
    margin-top: 4px;
    padding: 8px;
}
QTabBar::tab {
    background: #1e1e2e;
    color: #a6adc8;
    padding: 10px 20px;
    margin-right: 4px;
    border-radius: 8px 8px 0 0;
}
QTabBar::tab:selected { background: #313244; color: #89b4fa; font-weight: bold; }
QTabBar::tab:hover:!selected { background: #45475a; }
QGroupBox {
    color: #89b4fa; border: 1px solid #313244;
    border-radius: 8px; padding: 14px; margin-top: 12px;
}
QGroupBox::title { subcontrol-origin: margin; left: 16px; padding: 0 8px; background: #11111b; }
QTextEdit, QTextBrowser, QPlainTextEdit {
    background: #181825; color: #cdd6f4;
    border: 1px solid #313244; border-radius: 6px;
    padding: 10px; font-size: 13px; font-family: Consolas, monospace;
}
QComboBox {
    background: #1e1e2e; color: #cdd6f4;
    border: 1px solid #313244; border-radius: 6px; padding: 6px 12px;
}
QComboBox:hover { border-color: #89b4fa; }
QPushButton {
    background: #89b4fa; color: #1e1e2e; font-weight: bold;
    border-radius: 6px; padding: 8px 16px; border: none;
}
QPushButton:hover { background: #74c7ec; }
QPushButton:disabled { background: #313244; color: #6c7086; }
QPushButton#secondary { background: #313244; color: #cdd6f4; font-weight: normal; }
QPushButton#secondary:hover { background: #45475a; }
QPushButton#danger { background: #f38ba8; color: #1e1e2e; }
QProgressBar {
    border: 1px solid #313244; border-radius: 6px;
    background: #181825; height: 10px;
}
QProgressBar::chunk { background: #89b4fa; border-radius: 4px; }
QScrollArea { border: none; background: transparent; }
QFrame#card { background: #1e1e2e; border-radius: 8px; border: 1px solid #313244; padding: 12px; }
"""

STYLE_LIGHT = """
QMainWindow, QWidget { background: #f5f5f5; color: #333; }
QLabel { color: #333; }
QTabWidget::pane {
    border: 1px solid #ddd;
    border-radius: 10px;
    background: #fff;
    margin-top: 4px;
    padding: 8px;
}
QTabBar::tab {
    background: #e8e8e8;
    color: #555;
    padding: 10px 20px;
    margin-right: 4px;
    border-radius: 8px 8px 0 0;
}
QTabBar::tab:selected { background: #fff; color: #2563eb; font-weight: bold; }
QTabBar::tab:hover:!selected { background: #e0e0e0; }
QGroupBox {
    color: #2563eb; border: 1px solid #ddd;
    border-radius: 8px; padding: 14px; margin-top: 12px;
}
QGroupBox::title { subcontrol-origin: margin; left: 16px; padding: 0 8px; background: #fff; }
QTextEdit, QTextBrowser, QPlainTextEdit {
    background: #fff; color: #333;
    border: 1px solid #ddd; border-radius: 6px;
    padding: 10px; font-size: 13px; font-family: Consolas, monospace;
}
QComboBox {
    background: #fff; color: #333;
    border: 1px solid #ddd; border-radius: 6px; padding: 6px 12px;
}
QComboBox:hover { border-color: #2563eb; }
QPushButton {
    background: #2563eb; color: #fff; font-weight: bold;
    border-radius: 6px; padding: 8px 16px; border: none;
}
QPushButton:hover { background: #1d4ed8; }
QPushButton:disabled { background: #94a3b8; color: #64748b; }
QPushButton#secondary { background: #e2e8f0; color: #333; font-weight: normal; }
QPushButton#secondary:hover { background: #cbd5e1; }
QPushButton#danger { background: #dc2626; color: #fff; }
QProgressBar {
    border: 1px solid #ddd; border-radius: 6px;
    background: #f1f5f9; height: 10px;
}
QProgressBar::chunk { background: #2563eb; border-radius: 4px; }
QScrollArea { border: none; background: transparent; }
QFrame#card { background: #fff; border-radius: 8px; border: 1px solid #ddd; padding: 12px; }
"""

THEME = "dark"

LANG_MAP = {0: "auto", 1: "es", 2: "en", 3: "fr", 4: "de", 5: "pt", 6: "ja"}


# --------------------------------------------------------------------------- #
# Worker                                                                      #
# --------------------------------------------------------------------------- #

class AnalysisWorker(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    status = pyqtSignal(str)

    def __init__(self, payload: dict):
        super().__init__()
        self._payload = payload

    def run(self):
        try:
            from backend.analyzer import run_analysis
            from backend.file_scanner import scan_mod_folders
            from backend.local_investigator import investigate

            mods_path_str = self._payload.get("mods_base_path")
            bug = self._payload.get("bug_description", "")
            mods = self._payload.get("mods", [])
            file_conflicts = self._payload.get("file_conflicts", [])
            overwrite = self._payload.get("overwrite_files", [])

            file_investigation = ""
            if mods_path_str:
                mods_path = Path(mods_path_str)
                if mods_path.exists():
                    self.status.emit("Investigando carpetas de mods…")
                    try:
                        inv = investigate(bug, file_conflicts, overwrite, mods)
                        file_investigation = scan_mod_folders(
                            mods_path, mods, bug,
                            mods_to_prioritize=inv.get("priority_mods", []),
                        )
                    except Exception:
                        pass

            self._payload["file_investigation_summary"] = file_investigation
            self._payload.pop("mods_base_path", None)
            self.status.emit("Analizando (IA + web)…")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    run_analysis(
                        mods=self._payload.get("mods", []),
                        plugins=self._payload.get("plugins", []),
                        bug_description=bug,
                        load_order=self._payload.get("load_order", []),
                        file_conflicts=self._payload.get("file_conflicts", []),
                        overwrite_files=self._payload.get("overwrite_files", []),
                        mod_metadata=self._payload.get("mod_metadata", []),
                        skyrim_version=self._payload.get("skyrim_version"),
                        skse_version=self._payload.get("skse_version"),
                        papyrus_errors=self._payload.get("papyrus_errors", []),
                        skse_errors=self._payload.get("skse_errors", []),
                        response_language=self._payload.get("response_language", "auto"),
                        include_web_search=self._payload.get("include_web_search", True),
                        file_investigation_summary=file_investigation,
                    )
                )
                self.finished.emit(result)
            finally:
                loop.close()
        except Exception as exc:
            self.error.emit(str(exc))


# --------------------------------------------------------------------------- #
# Main window                                                                 #
# --------------------------------------------------------------------------- #

class StandaloneApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self._env_data = {}
        self._mo2_path = None
        self._profile_name = None
        self._worker = None
        self._last_result = None
        init_db()
        self._apply_theme()
        self._build_ui()
        self._auto_detect()

    def _build_ui(self):
        self.setWindowTitle(f"AI Conflict Analyzer  v{VERSION}")
        self.setMinimumSize(1000, 750)
        self.resize(1050, 800)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(8)
        root.setContentsMargins(16, 16, 16, 16)

        # Header con acciones rápidas
        header = QHBoxLayout()
        title = QLabel("🔍  AI Conflict Analyzer")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #89b4fa;")
        header.addWidget(title)
        header.addStretch()

        self.btn_mo2 = QPushButton("📂 Abrir MO2")
        self.btn_mo2.setObjectName("secondary")
        self.btn_mo2.setToolTip("Abrir Mod Organizer 2")
        self.btn_mo2.clicked.connect(self._open_mo2)
        self.btn_mo2.setVisible(False)
        header.addWidget(self.btn_mo2)

        self.btn_overwrite = QPushButton("📁 Overwrite")
        self.btn_overwrite.setObjectName("secondary")
        self.btn_overwrite.setToolTip("Abrir carpeta Overwrite de MO2")
        self.btn_overwrite.clicked.connect(self._open_overwrite)
        self.btn_overwrite.setVisible(False)
        header.addWidget(self.btn_overwrite)

        self.btn_history = QPushButton("📜 Historial")
        self.btn_history.setObjectName("secondary")
        self.btn_history.setToolTip("Ver historial de análisis")
        self.btn_history.clicked.connect(self._show_history)
        header.addWidget(self.btn_history)

        self.btn_theme = QPushButton("🌓 Tema")
        self.btn_theme.setObjectName("secondary")
        self.btn_theme.setToolTip("Alternar tema claro/oscuro")
        self.btn_theme.clicked.connect(self._toggle_theme)
        header.addWidget(self.btn_theme)

        root.addLayout(header)

        # Path selection (compacto)
        path_row = QHBoxLayout()
        path_row.addWidget(QLabel("Juego:"))
        self.game_combo = QComboBox()
        self.game_combo.addItems(["Skyrim SE", "Fallout 4"])
        self.game_combo.setMinimumWidth(100)
        path_row.addWidget(self.game_combo)
        path_row.addWidget(QLabel("MO2:"))
        self.mo2_combo = QComboBox()
        self.mo2_combo.setMinimumWidth(260)
        self.mo2_combo.currentIndexChanged.connect(self._on_mo2_changed)
        path_row.addWidget(self.mo2_combo)
        btn_browse = QPushButton("Examinar…")
        btn_browse.setObjectName("secondary")
        btn_browse.clicked.connect(self._browse_mo2)
        path_row.addWidget(btn_browse)
        path_row.addWidget(QLabel("Perfil:"))
        self.profile_combo = QComboBox()
        self.profile_combo.setMinimumWidth(130)
        path_row.addWidget(self.profile_combo)
        btn_reload = QPushButton("↺ Recargar")
        btn_reload.setObjectName("secondary")
        btn_reload.clicked.connect(self._load_env)
        path_row.addWidget(btn_reload)
        path_row.addStretch()
        root.addLayout(path_row)

        self.env_label = QLabel("Selecciona MO2 y perfil, luego Recargar.")
        self.env_label.setWordWrap(True)
        self.env_label.setStyleSheet("color:#a6e3a1; font-size:12px;")
        root.addWidget(self.env_label)

        # Tabs
        self._tabs = QTabWidget()
        tabs = self._tabs
        tabs.addTab(self._tab_analisis(), "🔬 Análisis IA")
        tabs.addTab(self._tab_preflight(), "🩺 Pre-vuelo")
        tabs.addTab(self._tab_conflictos(), "⚔️ Conflictos")
        tabs.addTab(self._tab_loadorder(), "📋 Load order")
        tabs.addTab(self._tab_conocimiento(), "📚 Mi base de conocimiento")
        tabs.addTab(self._tab_buenas_practicas(), "✅ Buenas prácticas")
        root.addWidget(tabs)

        # Atajo Ctrl+Enter para analizar
        try:
            self._shortcut_analyze = QShortcut(QKeySequence("Ctrl+Return"), self)
        except TypeError:
            self._shortcut_analyze = QShortcut(QKeySequence("Ctrl+Enter"), self)
        self._shortcut_analyze.activated.connect(self._run)

    def _tab_analisis(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        opts = QGroupBox("Opciones")
        opts_row = QHBoxLayout(opts)
        self.chk_conflicts = QCheckBox("Conflictos de archivos")
        self.chk_conflicts.setChecked(True)
        self.chk_papyrus = QCheckBox("Logs Papyrus / SKSE")
        self.chk_papyrus.setChecked(True)
        self.chk_web = QCheckBox("Reddit / Nexus tiempo real")
        self.chk_web.setChecked(True)
        opts_row.addWidget(self.chk_conflicts)
        opts_row.addWidget(self.chk_papyrus)
        opts_row.addWidget(self.chk_web)
        opts_row.addStretch()
        opts_row.addWidget(QLabel("Idioma:"))
        self.lang_combo = QComboBox()
        self.lang_combo.addItems([
            "🌐 Auto", "🇲🇽 Español", "🇺🇸 English",
            "🇫🇷 Français", "🇩🇪 Deutsch", "🇧🇷 Português", "🇯🇵 日本語",
        ])
        opts_row.addWidget(self.lang_combo)
        lay.addWidget(opts)

        bug_label = QLabel("Describe el bug:")
        bug_label.setStyleSheet("color:#89b4fa; font-weight:bold;")
        lay.addWidget(bug_label)
        # Plantillas de bugs
        tpl_row = QHBoxLayout()
        for label, text in BUG_TEMPLATES:
            btn = QPushButton(label)
            btn.setObjectName("secondary")
            btn.setMaximumWidth(180)
            btn.clicked.connect(lambda checked, t=text: self.bug_input.setPlainText(t))
            tpl_row.addWidget(btn)
        tpl_row.addStretch()
        lay.addLayout(tpl_row)
        self.bug_input = QTextEdit()
        self.bug_input.setPlaceholderText(
            "Ej: ojos blancos · cara negra · T-pose · CTD en Whiterun · SkyUI no carga"
        )
        self.bug_input.setMaximumHeight(80)
        lay.addWidget(self.bug_input)

        btn_row = QHBoxLayout()
        self.btn_analyze = QPushButton("🔬 Analizar con IA")
        self.btn_analyze.setToolTip("Ctrl+Enter para analizar rápido")
        self.btn_analyze.clicked.connect(self._run)
        self.btn_save = QPushButton("💾 Guardar reporte")
        self.btn_save.setObjectName("secondary")
        self.btn_save.clicked.connect(self._save_report)
        btn_row.addWidget(self.btn_analyze)
        btn_row.addWidget(self.btn_save)
        btn_row.addStretch()
        lay.addLayout(btn_row)

        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("color:#f9e2af; font-size:12px;")
        lay.addWidget(self.lbl_status)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        lay.addWidget(self.progress)

        self.results = QTextBrowser()
        self.results.setOpenExternalLinks(True)
        lay.addWidget(self.results)
        return w

    def _tab_preflight(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        self.preflight_label = QLabel("Recarga el entorno para ejecutar el pre-vuelo.")
        self.preflight_label.setWordWrap(True)
        self.preflight_label.setStyleSheet("color:#bac2de; padding:8px;")
        lay.addWidget(self.preflight_label)
        self.preflight_list = QTextBrowser()
        self.preflight_list.setOpenExternalLinks(True)
        lay.addWidget(self.preflight_list)
        return w

    def _refresh_preflight(self):
        game_path = self._env_data.get("game_path")
        game_name = self._env_data.get("game_name", "Skyrim SE")
        if game_path:
            game_path = Path(game_path) if isinstance(game_path, str) else game_path
        else:
            game_path = detect_fallout4_path() if "fallout" in game_name.lower() else detect_skyrim_path()
        mods = self._env_data.get("mods", [])
        plugins = self._env_data.get("plugins", [])
        mo2_path = getattr(self, "_mo2_path", None)
        results = run_preflight(game_path, mods, plugins, game_name=game_name, mo2_path=mo2_path)
        lines = []
        for r in results:
            icon = "✓" if r["ok"] else "⚠️"
            color = "#a6e3a1" if r["ok"] else "#f38ba8"
            lines.append(f'<span style="color:{color}">{icon} {r["name"]}: {r["message"]}</span>')
        self.preflight_list.setHtml("<br>".join(lines))
        self.preflight_label.setText("Resultados del pre-vuelo:")

    def _tab_conflictos(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        self.conflict_summary = QLabel("Recarga el entorno para ver conflictos de archivos.")
        self.conflict_summary.setWordWrap(True)
        self.conflict_summary.setStyleSheet("color:#bac2de; padding:8px;")
        lay.addWidget(self.conflict_summary)
        self.conflict_list = QTextBrowser()
        self.conflict_list.setOpenExternalLinks(True)
        lay.addWidget(self.conflict_list)
        return w

    def _tab_loadorder(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lo_btns = QHBoxLayout()
        self.btn_copy_order = QPushButton("📋 Copiar load order")
        self.btn_copy_order.setObjectName("secondary")
        self.btn_copy_order.clicked.connect(self._copy_loadorder)
        self.btn_export_plugins = QPushButton("💾 Exportar plugins.txt")
        self.btn_export_plugins.setObjectName("secondary")
        self.btn_export_plugins.clicked.connect(self._export_plugins_txt)
        self.btn_suggest_order = QPushButton("🔄 Sugerir orden (heurística)")
        self.btn_suggest_order.setObjectName("secondary")
        self.btn_suggest_order.clicked.connect(self._suggest_loadorder)
        self.btn_loot = QPushButton("🃏 Ejecutar LOOT")
        self.btn_loot.setObjectName("secondary")
        self.btn_loot.clicked.connect(self._run_loot)
        self._update_loot_tooltip()
        self.btn_compare = QPushButton("Comparar perfiles")
        self.btn_compare.setObjectName("secondary")
        self.btn_compare.clicked.connect(self._compare_profiles)
        lo_btns.addWidget(self.btn_copy_order)
        lo_btns.addWidget(self.btn_export_plugins)
        lo_btns.addWidget(self.btn_suggest_order)
        lo_btns.addWidget(self.btn_loot)
        lo_btns.addWidget(self.btn_compare)
        lo_btns.addStretch()
        lay.addLayout(lo_btns)
        self.loadorder_label = QLabel("Orden actual vs sugerido (usa LOOT para orden definitivo):")
        lay.addWidget(self.loadorder_label)
        self.loadorder_text = QTextEdit()
        self.loadorder_text.setReadOnly(True)
        self.loadorder_text.setFont(QFont("Consolas", 10))
        lay.addWidget(self.loadorder_text)
        return w

    def _tab_buenas_practicas(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        try:
            scroll.setFrameShape(QFrame.Shape.NoFrame)
        except AttributeError:
            scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background:transparent;")
        content = QWidget()
        lay = QVBoxLayout(content)
        lay.addWidget(QLabel("Mods y herramientas recomendadas para Skyrim SE:"))
        for bp in BEST_PRACTICES:
            card = QFrame()
            card.setObjectName("card")
            card_lay = QVBoxLayout(card)
            title = QLabel(f"• {bp['name']}")
            title.setStyleSheet("font-weight:bold; color:#89b4fa;")
            title.setWordWrap(True)
            card_lay.addWidget(title)
            desc = QLabel(bp["desc"])
            desc.setWordWrap(True)
            desc.setStyleSheet("color:#bac2de; font-size:12px;")
            card_lay.addWidget(desc)
            link_btn = QPushButton(f"🔗 {bp['link'][:50]}…")
            link_btn.setObjectName("secondary")
            try:
                link_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            except AttributeError:
                link_btn.setCursor(QCursor(Qt.PointingHandCursor))
            link_btn.setStyleSheet("text-align:left; padding:4px;")
            link_btn.clicked.connect(lambda checked, u=bp["link"]: self._open_url(u))
            card_lay.addWidget(link_btn)
            lay.addWidget(card)
        lay.addStretch()
        scroll.setWidget(content)
        return scroll

    def _tab_conocimiento(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        kb_path = ROOT / "knowledge_base" / "conflicts.json"
        btn_row = QHBoxLayout()
        btn_load = QPushButton("Cargar")
        btn_load.setObjectName("secondary")
        btn_load.clicked.connect(lambda: self._load_knowledge_base())
        btn_save = QPushButton("Guardar")
        btn_save.setObjectName("secondary")
        btn_save.clicked.connect(lambda: self._save_knowledge_base())
        btn_row.addWidget(btn_load)
        btn_row.addWidget(btn_save)
        btn_row.addStretch()
        lay.addLayout(btn_row)
        self.kb_edit = QPlainTextEdit()
        self.kb_edit.setPlaceholderText("Contenido de knowledge_base/conflicts.json (JSON)")
        self._kb_path = kb_path
        lay.addWidget(self.kb_edit)
        if kb_path.exists():
            try:
                data = json.loads(kb_path.read_text(encoding="utf-8"))
                self.kb_edit.setPlainText(json.dumps(data, indent=2, ensure_ascii=False))
            except Exception:
                pass
        return w

    def _load_knowledge_base(self):
        if self._kb_path.exists():
            try:
                data = json.loads(self._kb_path.read_text(encoding="utf-8"))
                self.kb_edit.setPlainText(json.dumps(data, indent=2, ensure_ascii=False))
                QMessageBox.information(self, "Cargar", "Base de conocimiento cargada.")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"No se pudo cargar: {e}")

    def _save_knowledge_base(self):
        try:
            text = self.kb_edit.toPlainText()
            json.loads(text)
            self._kb_path.write_text(text, encoding="utf-8")
            QMessageBox.information(self, "Guardar", "Base de conocimiento guardada.")
        except json.JSONDecodeError as e:
            QMessageBox.warning(self, "Error", f"JSON inválido: {e}")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo guardar: {e}")

    def _open_url(self, url: str):
        if sys.platform == "win32":
            os.startfile(url)
        else:
            subprocess.run(["xdg-open", url], check=False)

    def _apply_theme(self):
        global THEME
        style = STYLE_DARK if THEME == "dark" else STYLE_LIGHT
        self.setStyleSheet(style)

    def _toggle_theme(self):
        global THEME
        THEME = "light" if THEME == "dark" else "dark"
        self._apply_theme()

    def _update_loot_tooltip(self):
        mo2_path = getattr(self, "_mo2_path", None)
        loot_exe = detect_loot(mo2_path)
        if loot_exe:
            self.btn_loot.setToolTip(f"Ejecutar LOOT\nEncontrado: {loot_exe}")
        else:
            self.btn_loot.setToolTip("LOOT no detectado. Clic para abrir página de descarga.")

    def _run_loot(self):
        mo2_path = getattr(self, "_mo2_path", None)
        loot_exe = detect_loot(mo2_path)
        if loot_exe:
            subprocess.Popen([str(loot_exe)])
        else:
            msg = QMessageBox(self)
            try:
                msg.setIcon(QMessageBox.Icon.Information)
            except AttributeError:
                msg.setIcon(QMessageBox.Information)
            msg.setWindowTitle("LOOT no encontrado")
            msg.setText(
                "LOOT (Load Order Optimization Tool) no está instalado o no se detectó.\n\n"
                "LOOT ordena tus plugins automáticamente y evita muchos conflictos.\n"
                "Haz clic en 'Abrir descarga' para obtenerlo."
            )
            try:
                btn_dl = msg.addButton("Abrir descarga", QMessageBox.ButtonRole.ActionRole)
                msg.addButton("Cerrar", QMessageBox.ButtonRole.AcceptRole)
            except AttributeError:
                btn_dl = msg.addButton("Abrir descarga", QMessageBox.ActionRole)
                msg.addButton("Cerrar", QMessageBox.AcceptRole)
            msg.setDefaultButton(btn_dl)
            msg.exec()
            try:
                if msg.clickedButton() == btn_dl:
                    self._open_url(LOOT_DOWNLOAD_URL)
            except Exception:
                pass

    def _compare_profiles(self):
        mo2_path = self.mo2_combo.currentData()
        if not mo2_path:
            QMessageBox.warning(self, "Comparar", "Selecciona MO2 primero.")
            return
        profiles = get_mo2_profiles(Path(mo2_path))
        if len(profiles) < 2:
            QMessageBox.information(self, "Comparar", "Necesitas al menos 2 perfiles para comparar.")
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("Comparar perfiles")
        lay = QVBoxLayout(dlg)
        row = QHBoxLayout()
        row.addWidget(QLabel("Perfil A:"))
        combo_a = QComboBox()
        combo_a.addItems(profiles)
        row.addWidget(combo_a)
        row.addWidget(QLabel("Perfil B:"))
        combo_b = QComboBox()
        combo_b.addItems(profiles)
        combo_b.setCurrentIndex(1 if len(profiles) > 1 else 0)
        row.addWidget(combo_b)
        lay.addLayout(row)
        result_edit = QTextEdit()
        result_edit.setReadOnly(True)
        lay.addWidget(result_edit)
        btn_row = QHBoxLayout()
        btn_compare = QPushButton("Comparar")
        btn_compare.clicked.connect(lambda: _do_compare())
        btn_close = QPushButton("Cerrar")
        btn_close.setObjectName("secondary")
        btn_close.clicked.connect(dlg.accept)
        btn_row.addWidget(btn_compare)
        btn_row.addWidget(btn_close)
        lay.addLayout(btn_row)

        def _do_compare():
            pa, pb = combo_a.currentText(), combo_b.currentText()
            if pa == pb:
                result_edit.setPlainText("Selecciona perfiles diferentes.")
                return
            skyrim = detect_skyrim_path()
            game_docs = get_game_docs_path(skyrim) if skyrim else None
            try:
                env_a = collect_from_mo2(Path(mo2_path), pa, skyrim, game_docs, False)
                env_b = collect_from_mo2(Path(mo2_path), pb, skyrim, game_docs, False)
            except Exception as e:
                result_edit.setPlainText(f"Error: {e}")
                return
            mods_a = set(env_a.get("mods", []))
            mods_b = set(env_b.get("mods", []))
            only_a = mods_a - mods_b
            only_b = mods_b - mods_a
            lines = [f"En A no en B ({len(only_a)}):", ""] + sorted(only_a) + ["", f"En B no en A ({len(only_b)}):", ""] + sorted(only_b)
            result_edit.setPlainText("\n".join(lines))

        dlg.exec()

    def _show_history(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Historial de análisis")
        dlg.setMinimumSize(500, 400)
        lay = QVBoxLayout(dlg)
        lst = QListWidget()
        for item in get_recent(10):
            lst.addItem(QListWidgetItem(f"{item['created_at'][:19]} — {item['bug'][:60]}…" if len(item['bug']) > 60 else f"{item['created_at'][:19]} — {item['bug']}"))
            lst.item(len(lst) - 1).setData(USER_ROLE, item)
        lst.itemDoubleClicked.connect(lambda: self._on_history_item_double_click(lst, dlg))
        lay.addWidget(lst)
        btn_clear = QPushButton("Borrar historial")
        btn_clear.setObjectName("danger")
        btn_clear.clicked.connect(lambda: (clear_history(), lst.clear(), None))
        lay.addWidget(btn_clear)
        dlg.exec()

    def _on_history_item_double_click(self, lst: QListWidget, dlg: QDialog):
        item = lst.currentItem()
        if not item:
            return
        data = item.data(USER_ROLE)
        if not data:
            return
        try:
            result = json.loads(data["result_json"])
            self._last_result = result
            self.results.setHtml(_format(result))
            if hasattr(self, "_tabs"):
                self._tabs.setCurrentIndex(0)
            dlg.accept()
        except Exception:
            pass

    def _open_mo2(self):
        if not self._mo2_path:
            return
        exe = self._mo2_path / "ModOrganizer.exe"
        if exe.exists():
            subprocess.Popen([str(exe)], cwd=str(self._mo2_path))

    def _open_overwrite(self):
        if not self._mo2_path:
            return
        ow = self._mo2_path / "overwrite"
        if ow.exists():
            if sys.platform == "win32":
                os.startfile(str(ow))
            else:
                subprocess.run(["xdg-open", str(ow)], check=False)

    def _copy_loadorder(self):
        order = self._env_data.get("load_order") or self._env_data.get("plugins", [])
        if not order:
            QMessageBox.information(self, "Load order", "Recarga el entorno primero.")
            return
        text = "\n".join(order)
        app = QApplication.instance()
        cb = app.clipboard()
        cb.setText(text)
        QMessageBox.information(self, "Copiado", "Load order copiado al portapapeles.")

    def _export_plugins_txt(self):
        order = self._env_data.get("load_order") or self._env_data.get("plugins", [])
        if not order:
            QMessageBox.information(self, "Exportar", "Recarga el entorno primero.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Guardar plugins.txt", "plugins.txt",
            "Text (*.txt);;Todos (*.*)",
        )
        if not path:
            return
        lines = []
        for p in order:
            lines.append(f"*{p}" if not p.startswith("*") else p)
        Path(path).write_text("\n".join(lines), encoding="utf-8")
        QMessageBox.information(self, "Guardado", f"Exportado a:\n{path}")

    def _suggest_loadorder(self):
        order = self._env_data.get("load_order") or self._env_data.get("plugins", [])
        if not order:
            QMessageBox.information(self, "Load order", "Recarga el entorno primero.")
            return
        suggested = suggest_plugin_order(list(order))
        diff = []
        for i, (curr, sugg) in enumerate(zip(order, suggested)):
            mark = "✓" if curr == sugg else "→"
            diff.append(f"{mark} {i+1:3d}. {sugg}" + (f" (antes: {curr})" if curr != sugg else ""))
        self.loadorder_text.setPlainText(
            "ORDEN SUGERIDO (heurística: masters primero, patches al final):\n"
            "Usa LOOT para el orden definitivo.\n\n" + "\n".join(diff)
        )

    def _auto_detect(self):
        mo2_list = detect_mo2_paths()
        self.mo2_combo.clear()
        self.mo2_combo.addItem("— Selecciona MO2 —", None)
        for p in mo2_list:
            self.mo2_combo.addItem(str(p), str(p))
        if mo2_list:
            self.mo2_combo.setCurrentIndex(1)

    def _on_mo2_changed(self):
        path = self.mo2_combo.currentData()
        self.profile_combo.clear()
        if path:
            profiles = get_mo2_profiles(Path(path))
            self.profile_combo.addItems(profiles if profiles else ["(sin perfiles)"])
        else:
            self.profile_combo.addItem("(selecciona MO2)")

    def _browse_mo2(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Carpeta Mod Organizer 2", "")
        if not dir_path:
            return
        path = Path(dir_path)
        if not (path / "ModOrganizer.exe").exists():
            QMessageBox.warning(self, "MO2", "No se encontró ModOrganizer.exe ahí.")
            return
        idx = self.mo2_combo.findData(str(path))
        if idx < 0:
            self.mo2_combo.addItem(str(path), str(path))
            idx = self.mo2_combo.count() - 1
        self.mo2_combo.setCurrentIndex(idx)

    def _load_env(self):
        mo2_path = self.mo2_combo.currentData()
        profile_name = self.profile_combo.currentText()
        if not mo2_path or not profile_name or profile_name.startswith("("):
            self.env_label.setText("⚠️  Selecciona MO2 y un perfil válido.")
            self.env_label.setStyleSheet("color:#f38ba8; font-size:12px;")
            return
        try:
            self._mo2_path = Path(mo2_path)
            self._profile_name = profile_name
            game_name = self.game_combo.currentText()
            if game_name == "Fallout 4":
                game_path = detect_fallout4_path()
                game_docs = get_fallout4_docs_path() if game_path else None
            else:
                game_path = detect_skyrim_path()
                game_docs = get_game_docs_path(game_path) if game_path else None
            self._env_data = collect_from_mo2(
                mo2_path=Path(mo2_path),
                profile_name=profile_name,
                game_path=game_path,
                game_docs_path=game_docs,
                include_file_conflicts=self.chk_conflicts.isChecked(),
            )
            self._env_data["game_path"] = str(game_path) if game_path else None
            self._env_data["game_name"] = game_name
            n_mods = len(self._env_data.get("mods", []))
            n_plugins = len(self._env_data.get("plugins", []))
            n_conflicts = len(self._env_data.get("file_conflicts", []))
            n_overwrite = len(self._env_data.get("overwrite_files", []))
            sky_ver = self._env_data.get("skyrim_version") or "—"
            skse_ver = self._env_data.get("skse_version") or "—"
            ver_str = f"{sky_ver} · {skse_ver}" if game_name == "Skyrim SE" else "FO4"

            self.env_label.setText(
                f"✅ {game_name} · {n_mods} mods · {n_plugins} plugins · {n_conflicts} conflictos · "
                f"{n_overwrite} overwrite · {ver_str}"
            )
            self.env_label.setStyleSheet("color:#a6e3a1; font-size:12px;")

            self.btn_mo2.setVisible(True)
            self.btn_overwrite.setVisible(True)

            # Tab Conflictos
            self._refresh_conflict_tab()
            # LOOT button tooltip
            self._update_loot_tooltip()
            # Tab Pre-vuelo
            self._refresh_preflight()
            # Tab Load order
            order = self._env_data.get("load_order") or self._env_data.get("plugins", [])
            self.loadorder_text.setPlainText("\n".join(f"{i+1:3d}. {p}" for i, p in enumerate(order)))

        except Exception as exc:
            self.env_label.setText(f"⚠️ Error: {exc}")
            self.env_label.setStyleSheet("color:#f38ba8; font-size:12px;")

    def _refresh_conflict_tab(self):
        conflicts = self._env_data.get("file_conflicts", [])
        if not conflicts:
            self.conflict_summary.setText("Sin conflictos de archivos detectados (o desactivaste la opción).")
            self.conflict_list.setPlainText("")
            return
        self.conflict_summary.setText(f"Top {min(50, len(conflicts))} conflictos — Mapa: archivo → mods en pugna (gana el último):")
        # Agrupar por extensión para vista más clara
        by_ext = {}
        for c in conflicts[:50]:
            ext = Path(c["file"]).suffix or "(sin ext)"
            by_ext.setdefault(ext, []).append(c)
        lines = []
        for ext in sorted(by_ext.keys(), key=lambda e: -len(by_ext[e])):
            lines.append(f"\n═══ {ext} ({len(by_ext[ext])}) ═══")
            for c in by_ext[ext]:
                vs = " vs ".join(c["mods"][:4])
                lines.append(f"  📄 {c['file']}")
                lines.append(f"     {vs} → gana: {c['winner']}")
        self.conflict_list.setPlainText("\n".join(lines).strip())

    def _run(self):
        bug = self.bug_input.toPlainText().strip()
        if not bug:
            QMessageBox.warning(self, "Sin descripción", "Escribe el bug antes de analizar.")
            return
        if not self._env_data.get("mods") and not self._env_data.get("plugins"):
            QMessageBox.warning(self, "Sin datos", "Recarga el entorno primero.")
            return

        env = dict(self._env_data)
        if not self.chk_papyrus.isChecked():
            env["papyrus_errors"] = []
            env["skse_errors"] = []
        if not self.chk_conflicts.isChecked():
            env["file_conflicts"] = []

        # Run preflight to get diagnostic data for the AI
        game_path = self._env_data.get("game_path")
        game_path = Path(game_path) if game_path else None
        preflight = run_preflight(
            game_path,
            env.get("mods", []),
            env.get("plugins", []),
            game_name=env.get("game_name", "Skyrim SE"),
            mo2_path=self._mo2_path
        )

        # Map language codes to full names for the AI
        lang_code = LANG_MAP.get(self.lang_combo.currentIndex(), "auto")
        lang_name = lang_code
        if lang_code == "es": lang_name = "Spanish"
        elif lang_code == "en": lang_name = "English"
        elif lang_code == "fr": lang_name = "French"
        elif lang_code == "de": lang_name = "German"
        elif lang_code == "pt": lang_name = "Portuguese"
        elif lang_code == "ja": lang_name = "Japanese"

        payload = {
            "mods": env.get("mods", []),
            "plugins": env.get("plugins", []),
            "load_order": env.get("load_order", []),
            "bug_description": bug,
            "file_conflicts": env.get("file_conflicts", []),
            "overwrite_files": env.get("overwrite_files", []),
            "mod_metadata": env.get("mod_metadata", []),
            "skyrim_version": env.get("skyrim_version"),
            "skse_version": env.get("skse_version"),
            "papyrus_errors": env.get("papyrus_errors", []),
            "skse_errors": env.get("skse_errors", []),
            "response_language": lang_name,
            "include_web_search": self.chk_web.isChecked(),
            "mods_base_path": str(self._mo2_path / "mods") if self._mo2_path else None,
            "preflight_results": preflight,
        }

        self.btn_analyze.setEnabled(False)
        self.progress.show()
        self.results.clear()
        self.lbl_status.setText("Investigando… (puede tardar minutos — sin timeout)")

        self._worker = AnalysisWorker(payload)
        self._worker.status.connect(self.lbl_status.setText)
        self._worker.finished.connect(self._on_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_done(self, result: dict):
        self.progress.hide()
        self.btn_analyze.setEnabled(True)
        self.lbl_status.setText("✅ Análisis completado.")
        self._last_result = result
        self.results.setHtml(_format(result))
        try:
            save_analysis(self.bug_input.toPlainText().strip(), result)
        except Exception:
            pass

    def _on_error(self, msg: str):
        self.progress.hide()
        self.btn_analyze.setEnabled(True)
        self.lbl_status.setText("")
        self.results.setPlainText(f"Error:\n{msg}")

    def _save_report(self):
        if not self._last_result:
            QMessageBox.information(self, "Guardado", "Analiza primero.")
            return
        try:
            from datetime import datetime
            default_name = f"AI-Conflict-Report-{datetime.now().strftime('%Y%m%d-%H%M')}.html"
            path, _ = QFileDialog.getSaveFileName(
                self, "Guardar reporte", default_name,
                "HTML (*.html);;Texto (*.txt);;Todos (*.*)",
            )
            if not path:
                return
            html = _format(self._last_result)
            if path.lower().endswith(".html"):
                Path(path).write_text(
                    f"<!DOCTYPE html><html><head><meta charset='utf-8'/></head><body>{html}</body></html>",
                    encoding="utf-8",
                )
            else:
                lines = []
                for s in self._last_result.get("suspects", []):
                    lines.append(f"- {s['mod']} ({int(s['confidence']*100)}%): {s.get('reason','')}")
                    lines.append(f"  💡 {s.get('fix','')}")
                lines.append("")
                lines.append((self._last_result.get("explanation") or "").replace("\n", " "))
                for url in self._last_result.get("web_sources", []):
                    lines.append(url)
                Path(path).write_text("\n".join(lines), encoding="utf-8")
            QMessageBox.information(self, "Guardado", f"Guardado en:\n{path}")
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"No se pudo guardar: {exc}")


def _format(result: dict) -> str:
    import re
    html = "<style>body{font-family:Segoe UI;color:#cdd6f4;background:#181825;line-height:1.5}</style>"
    suspects = result.get("suspects", [])
    explanation = result.get("explanation", "")
    sources = result.get("web_sources", [])
    brief = result.get("investigation_brief", "")
    if brief:
        html += f"<h3 style='color:#89b4fa'>🔬 Investigación</h3><p style='color:#bac2de;font-size:12px'>{brief}</p>"
    if suspects:
        html += "<h3 style='color:#a6e3a1'>🎯 Mods sospechosos</h3><ul>"
        for s in suspects:
            pct = int(s["confidence"] * 100)
            color = "#a6e3a1" if pct >= 70 else "#f9e2af" if pct >= 40 else "#cdd6f4"
            html += (
                f"<li style='margin-bottom:10px'>"
                f"<b style='color:#89b4fa'>{s['mod']}</b> <span style='color:{color}'>{pct}%</span><br>"
                f"<small style='color:#bac2de'>{s.get('reason','')}</small><br>"
                f"<small style='color:#f9e2af'>💡 {s.get('fix','')}</small></li>"
            )
        html += "</ul>"
    if explanation:
        clean = re.sub(r"```json.*?```", "", explanation, flags=re.DOTALL)
        html += f"<h3 style='color:#cba6f7'>📝 Análisis</h3><p>{clean.replace(chr(10), '<br>')}</p>"
    html += "<h3 style='color:#74c7ec'>🌐 Fuentes</h3>"
    if sources:
        html += "<ul>" + "".join(f"<li><a href='{u}' style='color:#89b4fa' target='_blank'>{u}</a></li>" for u in sources) + "</ul>"
    else:
        html += "<p style='color:#6c7086'>Sin fuentes.</p>"
    if not suspects and not explanation:
        html += "<p>Sin resultados.</p>"
    return html


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = StandaloneApp()
    win.show()
    sys.exit(app.exec() if PYQT == 6 else app.exec_())


if __name__ == "__main__":
    main()
