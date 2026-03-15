# PyInstaller spec para AI Conflict Analyzer
# Uso: pyinstaller build_exe.spec

block_cipher = None
a = Analysis(
    ['run_standalone.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('knowledge_base', 'knowledge_base'),
        ('.env.example', '.'),
    ],
    hiddenimports=[
        'backend.analyzer', 'backend.llm', 'backend.knowledge', 'backend.web_search',
        'backend.local_investigator', 'backend.file_scanner', 'backend.search_planner',
        'scraper.scraper', 'scraper.nexus_api',
        'standalone.path_detector', 'standalone.standalone_reader', 'standalone.best_practices',
        'standalone.bug_templates', 'standalone.preflight_check', 'standalone.history',
        'standalone.loot_helper',
        'standalone.missing_masters',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='AI-Conflict-Analyzer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
)
