# AI Conflict Analyzer — Standalone

App independiente estilo **BodySlide** / **Nemesis** / **FINS**:
- No es plugin de MO2: corre por su cuenta
- Sin HTTP ni timeouts: todo in-process
- Detecta Skyrim y MO2 automáticamente
- Misma funcionalidad: análisis local + web + LLM

## Instalación

### 1. Python 3.10 o superior

```powershell
py --version
```

### 2. Dependencias

```powershell
cd "AI-Mod-Organizer-Analyzer"
pip install -r requirements.txt
```

Si PyQt6 da problemas en tu sistema:
```powershell
pip install PyQt5
```
(Luego habría que cambiar el import, pero suele funcionar PyQt6 en Windows.)

### 3. Ollama (modelo local)

```powershell
ollama pull qwen3:4b
```

O el modelo que tengas en `.env` (qwen2.5:7b, mistral:7b, etc.).

### 4. Ejecutar

```powershell
py run_standalone.py
```

## Uso

1. Si detectó MO2, elige carpeta y perfil
2. Si no, "Examinar…" y selecciona la carpeta de Mod Organizer 2
3. Clic en "↺ Recargar" para cargar mods/plugins
4. Describe el bug
5. "🔬 Analizar" — puede tardar varios minutos, **sin timeout**

## .exe (PyInstaller)

Para empaquetar como ejecutable independiente:

```powershell
pip install pyinstaller
py -m PyInstaller build_exe.spec
```

El archivo `AI-Conflict-Analyzer.exe` se genera en `dist/`. El spec incluye:
- `knowledge_base/` y `.env.example` empaquetados
- Todos los módulos backend, scraper y standalone
- Una sola ventana (sin consola)

**Importante:** Copia `.env` junto al .exe y configúralo con tu URL de Ollama y modelo.
