"""
Arranca el backend. Ejecutar desde la RAÍZ del proyecto:
  cd "c:\\...\\AI-Mod-Organizer-Analyzer"
  py run_backend.py

O desde aquí (backend/) con uvicorn desde la raíz:
  cd .. && py -m uvicorn backend.main:app --reload --port 8000
"""
import sys
from pathlib import Path

# Asegurar que la raíz del proyecto esté en el path
root = Path(__file__).resolve().parent.parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

import uvicorn

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
