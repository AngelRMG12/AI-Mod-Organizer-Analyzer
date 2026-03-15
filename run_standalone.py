"""
Lanza la app standalone de AI Conflict Analyzer.
Estilo BodySlide/Nemesis: sin plugin MO2, sin HTTP, sin timeouts.

Uso: py run_standalone.py
"""
import sys
from pathlib import Path

# Asegurar que la raíz está en el path
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from standalone.standalone_app import main

if __name__ == "__main__":
    main()
