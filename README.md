# AI Conflict Analyzer for Mod Organizer 2

A hybrid AI-powered plugin for **Mod Organizer 2** that reads your load order and mod list, and tells you exactly which mods are likely causing the bug you describe.

> Describe your bug → Get a list of suspect mods + fix suggestions, powered by local heuristics + LLM analysis.

---

## Features

- **MO2 Plugin (Python)** — Integrates directly into Mod Organizer 2's toolbar
- **Hybrid Analysis** — Fast offline heuristics + optional LLM (local or API)
- **Multi-language Support** — Knowledge base supports EN, ES, FR, DE, PT and more
- **Multiple LLM Providers** — Ollama (local/free), OpenAI, or any OpenAI-compatible API (LM Studio, Groq, etc.)
- **Knowledge Base Scraper** — Automatically crawls Reddit, Nexus Mods, and GitHub to discover and classify new conflicts
- **Open Knowledge Base** — Community-contributed JSON conflict database

---

## Architecture

```
MO2 Plugin (Python)
      │
      │  reads modlist.txt, plugins.txt
      ▼
Local Heuristic Search ──► knowledge_base/conflicts.json
      │
      ▼
FastAPI Backend
      │
      ├──► Ollama (local LLM, free)
      ├──► OpenAI API
      └──► Custom endpoint (LM Studio, Groq...)
      │
      ▼
Result: Suspect mods + confidence % + fix suggestion
```

---

## Project Structure

```
AI-Mod-Organizer-Analyzer/
├── plugin/
│   └── ai_conflict_analyzer/
│       ├── main.py          # MO2 plugin entry point + UI
│       └── reader.py        # modlist.txt / plugins.txt reader
├── backend/
│   ├── main.py              # FastAPI app
│   ├── analyzer.py          # Core analysis logic
│   ├── llm.py               # LLM abstraction (Ollama/OpenAI/custom)
│   ├── knowledge.py         # Knowledge base loader + heuristics
│   └── requirements.txt
├── scraper/
│   ├── scraper.py           # Knowledge base auto-scraper
│   └── requirements.txt
├── knowledge_base/
│   └── conflicts.json       # Community conflict database
├── .github/
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── ISSUE_TEMPLATE/
│       ├── bug_report.md
│       ├── feature_request.md
│       └── knowledge_base_entry.md
├── .env.example
├── CONTRIBUTING.md
└── CODE_OF_CONDUCT.md
```

---

## Installation

### 1. MO2 Plugin

1. Copy `plugin/ai_conflict_analyzer/` into your MO2 plugins folder:
   ```
   C:\Modding\MO2\plugins\ai_conflict_analyzer\
   ```
2. Restart Mod Organizer 2
3. Find **"AI Conflict Analyzer"** in the Tools menu

### 2. Backend (Optional but recommended)

Without the backend, only local heuristic analysis runs. The backend enables full LLM analysis.

```bash
cd backend
pip install -r requirements.txt
cp ../.env.example ../.env
# Edit .env with your LLM config
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 3. LLM Setup

**Option A — Ollama (Local, Free)**
```bash
# Install Ollama: https://ollama.com
ollama pull llama3
# Set in .env: LLM_PROVIDER=ollama
```

**Option B — OpenAI API**
```bash
# Set in .env:
# LLM_PROVIDER=openai
# OPENAI_API_KEY=sk-...
# OPENAI_MODEL=gpt-4o-mini
```

**Option C — LM Studio / Custom**
```bash
# Set in .env:
# LLM_PROVIDER=custom
# CUSTOM_LLM_URL=http://localhost:1234/v1
# CUSTOM_LLM_MODEL=mistral
```

---

## Usage

1. Open Mod Organizer 2
2. Click **AI Conflict Analyzer** in the toolbar
3. Describe your bug in natural language:
   > *"NPCs have black/dark faces"*
   > *"My character is stuck in T-pose"*
   > *"Game crashes when entering Whiterun"*
4. Click **Analyze**
5. Get results with suspect mods, confidence scores, and fix suggestions

---

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) first.

**Branch strategy:**
- `main` → Stable releases (maintainer-only merges)
- `dev` → Active development ← **Target all PRs here**

The easiest way to contribute is to **add a conflict entry** to `knowledge_base/conflicts.json`. See [CONTRIBUTING.md](CONTRIBUTING.md) for the format.

---

## Knowledge Base Scraper

The scraper automatically finds conflict reports online and uses a local LLM to classify them:

```bash
cd scraper
pip install -r requirements.txt
python scraper.py
```

The scraper crawls Reddit (`r/skyrimmods`, `r/FalloutMods`), Nexus Mods forums, and GitHub issues in multiple languages. Inspired by the automated content discovery approach used in [sammwyy/inkshelf](https://github.com/sammwyy/inkshelf).

---

## Roadmap

- [ ] Papyrus log analyzer (detect CTDs from stack traces)
- [ ] LOOT rule suggestions
- [ ] Overwrite conflict visualizer
- [ ] Web UI dashboard
- [ ] Auto-update knowledge base from community PRs

---

## License

MIT License — See [LICENSE](LICENSE) for details.
