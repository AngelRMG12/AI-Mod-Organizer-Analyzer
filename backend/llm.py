"""
LLM abstraction layer.
Supports:
  - OpenAI API (GPT-4o, GPT-3.5, etc.)
  - Ollama (local, free)
  - Any OpenAI-compatible endpoint (LM Studio, etc.)

Configure via environment variables (see .env.example).
"""

import os
from typing import Optional
from pathlib import Path
import httpx
from dotenv import load_dotenv

# Cargar .env desde raíz del proyecto y desde cwd
_env_paths = [
    Path(__file__).resolve().parent.parent / ".env",
    Path.cwd() / ".env",
    Path(__file__).resolve().parent.parent.parent / ".env",
]
for p in _env_paths:
    if p.exists():
        load_dotenv(p)
        break
else:
    load_dotenv()  # fallback a .env en cwd

LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "ollama")  # "openai" | "ollama" | "custom"
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2")
CUSTOM_LLM_URL = (os.environ.get("CUSTOM_LLM_URL", "") or "").strip().rstrip("/")
CUSTOM_LLM_KEY = (os.environ.get("CUSTOM_LLM_KEY", "") or "").strip()
CUSTOM_LLM_MODEL = (os.environ.get("CUSTOM_LLM_MODEL", "") or "").strip()


async def call_llm(prompt: str) -> dict:
    if LLM_PROVIDER == "openai":
        return await _call_openai(prompt)
    elif LLM_PROVIDER == "ollama":
        return await _call_ollama(prompt)
    elif LLM_PROVIDER == "custom":
        return await _call_custom(prompt)
    else:
        return {"content": f"Unknown LLM provider: {LLM_PROVIDER}", "tokens_used": 0}


async def _call_openai(prompt: str) -> dict:
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": OPENAI_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
    }
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        tokens = data.get("usage", {}).get("total_tokens")
        return {"content": content, "tokens_used": tokens}


async def _call_ollama(prompt: str) -> dict:
    # Ollama 0.3+ usa /api/chat (messages). Fallback a /api/generate por compatibilidad.
    payload_chat = {
        "model": OLLAMA_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
    }
    payload_generate = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
    }
    async with httpx.AsyncClient(timeout=120) as client:
        # Intentar primero /api/chat (versiones recientes)
        resp = await client.post(f"{OLLAMA_URL}/api/chat", json=payload_chat)
        if resp.status_code == 404:
            resp = await client.post(f"{OLLAMA_URL}/api/generate", json=payload_generate)
        resp.raise_for_status()
        data = resp.json()
        content = data.get("message", {}).get("content") or data.get("response", "")
        return {"content": content or "", "tokens_used": None}


async def _call_custom(prompt: str) -> dict:
    """Generic OpenAI-compatible endpoint (LM Studio, Groq, etc.)."""
    if not CUSTOM_LLM_KEY:
        raise ValueError(
            "CUSTOM_LLM_KEY vacía. Verifica que .env existe en la raíz del proyecto y contiene:\n"
            "CUSTOM_LLM_KEY=gsk_tu_key_aqui\n"
            "Obtén la key en https://console.groq.com"
        )
    headers = {
        "Authorization": f"Bearer {CUSTOM_LLM_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": CUSTOM_LLM_MODEL or "meta-llama/llama-4-scout-17b-16e-instruct",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
    }
    url = f"{CUSTOM_LLM_URL or 'https://api.groq.com/openai/v1'}/chat/completions"
    async with httpx.AsyncClient(timeout=90) as client:
        resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code != 200:
            try:
                err_body = resp.json()
                err_msg = err_body.get("error", {}).get("message", resp.text[:500])
            except Exception:
                err_msg = resp.text[:500]
            raise ValueError(
                f"Groq API error {resp.status_code}: {err_msg}\n"
                f"URL: {url}\nKey cargada: Sí ({len(CUSTOM_LLM_KEY)} chars)"
            )
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        tokens = data.get("usage", {}).get("total_tokens")
        return {"content": content, "tokens_used": tokens}
