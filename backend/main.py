"""
AI Conflict Analyzer - FastAPI Backend
Receives mod list + bug description and returns AI-powered conflict analysis.
Supports both local LLM (Ollama) and OpenAI-compatible APIs.
"""

import os
import json
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .analyzer import run_analysis

app = FastAPI(
    title="AI Conflict Analyzer",
    description="Backend for the MO2 AI Conflict Analyzer plugin",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --------------------------------------------------------------------------- #
# Schemas                                                                       #
# --------------------------------------------------------------------------- #

class AnalyzeRequest(BaseModel):
    mods: list[str]
    plugins: list[str]
    bug_description: str
    game: Optional[str] = "Skyrim SE"


class SuspectMod(BaseModel):
    mod: str
    confidence: float
    reason: str
    fix: Optional[str] = None


class AnalyzeResponse(BaseModel):
    suspects: list[SuspectMod]
    explanation: str
    tokens_used: Optional[int] = None
    web_sources: Optional[list[str]] = None


# --------------------------------------------------------------------------- #
# Routes                                                                        #
# --------------------------------------------------------------------------- #

@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.0"}


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest):
    if not req.mods and not req.plugins:
        raise HTTPException(status_code=400, detail="No mods or plugins provided.")
    if not req.bug_description.strip():
        raise HTTPException(status_code=400, detail="Bug description is required.")

    result = await run_analysis(
        mods=req.mods,
        plugins=req.plugins,
        bug_description=req.bug_description,
        game=req.game,
    )
    return result
