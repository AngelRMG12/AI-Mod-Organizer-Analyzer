# Contributing to AI Conflict Analyzer

First off, thank you for taking the time to contribute! 🎉

## How it works

- **`main`** — Stable releases only. **Only the maintainer merges here.**
- **`dev`** — Active development branch. All PRs target `dev`.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR_USERNAME/AI-Mod-Organizer-Analyzer.git`
3. Create a feature branch from `dev`:
   ```bash
   git checkout dev
   git pull origin dev
   git checkout -b feature/your-feature-name
   ```
4. Make your changes
5. Push and open a Pull Request **targeting `dev`** (not `main`)

## What You Can Contribute

| Area | Examples |
|------|---------|
| 🧠 Knowledge Base | Add new conflict entries to `knowledge_base/conflicts.json` |
| 🔌 Plugin | Improve the MO2 Python plugin UI/logic |
| ⚙️ Backend | Improve analysis, add new LLM providers |
| 🕷️ Scraper | Add new sources, improve classification |
| 📝 Docs | Fix typos, improve explanations, translate |
| 🐛 Bug Fixes | Fix anything broken |

## Adding to the Knowledge Base

The easiest way to contribute is to add a known bug/conflict entry to `knowledge_base/conflicts.json`:

```json
"your bug name": {
  "mods": ["ModName1", "ModName2"],
  "confidence": 0.8,
  "fix": "Brief description of the fix.",
  "sources": ["https://link-to-source"],
  "language": "en"
}
```

- `bug name` — lowercase, short keyword that appears in bug descriptions
- `mods` — list of mod names that commonly cause this bug
- `confidence` — float 0.0 to 1.0
- `fix` — actionable fix description
- `sources` — links to Nexus, Reddit, or GitHub where this was documented
- `language` — ISO 639-1 code (`en`, `es`, `fr`, `de`, `pt`, etc.)

## Pull Request Rules

- PRs must target the **`dev`** branch
- Include a clear description of what you changed and why
- Reference issues when applicable (`Fixes #42`)
- Keep PRs focused — one feature/fix per PR
- The maintainer ([@AngelRMG12](https://github.com/AngelRMG12)) reviews and merges to `main`

## Code Style

- Python: follow PEP 8, use type hints
- Keep functions small and focused
- No commented-out code in PRs

## Reporting Bugs

Use the **Bug Report** issue template. Include:
- What happened
- What you expected
- Your mod list (if relevant)
- Steps to reproduce

## Questions?

Open a [Discussion](https://github.com/AngelRMG12/AI-Mod-Organizer-Analyzer/discussions) — don't open issues for questions.
