"""
Arranca el backend desde la raíz del proyecto (necesario para los imports).
Uso: py run_backend.py
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
