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
import httpx

LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "ollama")  # "openai" | "ollama" | "custom"
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3")
CUSTOM_LLM_URL = os.environ.get("CUSTOM_LLM_URL", "")
CUSTOM_LLM_KEY = os.environ.get("CUSTOM_LLM_KEY", "")
CUSTOM_LLM_MODEL = os.environ.get("CUSTOM_LLM_MODEL", "")


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
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
    }
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(f"{OLLAMA_URL}/api/generate", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return {"content": data.get("response", ""), "tokens_used": None}


async def _call_custom(prompt: str) -> dict:
    """Generic OpenAI-compatible endpoint (LM Studio, Groq, etc.)."""
    headers = {
        "Authorization": f"Bearer {CUSTOM_LLM_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": CUSTOM_LLM_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
    }
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(f"{CUSTOM_LLM_URL}/chat/completions", json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        tokens = data.get("usage", {}).get("total_tokens")
        return {"content": content, "tokens_used": tokens}
