# Modelos Ollama para AI Conflict Analyzer

**Instalar dependencias:** `pip install beautifulsoup4` (para Nexus). Sin esto, solo usa Reddit.

`llama3.2` (3B) es rápido pero muy limitado. Para mejores resultados usa:

| Modelo       | Comando           | VRAM ~ | Calidad |
|-------------|-------------------|--------|---------|
| **qwen2.5:7b** | `ollama pull qwen2.5:7b`   | 4-6 GB | Excelente |
| **mistral:7b** | `ollama pull mistral:7b`   | 4-6 GB | Muy bueno |
| **llama3.2:11b** | `ollama pull llama3.2:11b` | 8 GB   | Mejor que 3B |
| **qwen2.5:14b** | `ollama pull qwen2.5:14b` | 10+ GB | Muy capaz |

En `.env` pon:
```
OLLAMA_MODEL=qwen2.5:7b
```
