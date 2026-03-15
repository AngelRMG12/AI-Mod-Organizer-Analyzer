"""
AI Conflict Analyzer - FastAPI Backend
"""

from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .analyzer import run_analysis

app = FastAPI(
    title="AI Conflict Analyzer",
    description="Full-environment mod conflict analysis with real-time web search",
    version="0.2.0",
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

class FileConflict(BaseModel):
    file: str
    mods: list[str]
    winner: str


class ModMeta(BaseModel):
    name: str
    version: Optional[str] = None
    nexus_id: Optional[str] = None
    category: Optional[str] = None


class AnalyzeRequest(BaseModel):
    # Core (required)
    mods: list[str]
    plugins: list[str]
    bug_description: str
    # Extended environment data (optional, sent by the MO2 plugin)
    load_order: Optional[list[str]] = None
    file_conflicts: Optional[list[FileConflict]] = None
    overwrite_files: Optional[list[str]] = None
    mod_metadata: Optional[list[ModMeta]] = None
    skyrim_version: Optional[str] = None
    skse_version: Optional[str] = None
    papyrus_errors: Optional[list[str]] = None
    skse_errors: Optional[list[str]] = None
    game: Optional[str] = "Skyrim SE"
    response_language: Optional[str] = "auto"
    include_web_search: Optional[bool] = True
    file_investigation_summary: Optional[str] = None


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
    investigation_brief: Optional[str] = None


# --------------------------------------------------------------------------- #
# Routes                                                                        #
# --------------------------------------------------------------------------- #

@app.get("/health")
def health():
    return {"status": "ok", "version": "0.2.0"}


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
        game=req.game or "Skyrim SE",
        load_order=req.load_order or [],
        file_conflicts=[fc.model_dump() for fc in (req.file_conflicts or [])],
        overwrite_files=req.overwrite_files or [],
        mod_metadata=[m.model_dump() for m in (req.mod_metadata or [])],
        skyrim_version=req.skyrim_version,
        skse_version=req.skse_version,
        papyrus_errors=req.papyrus_errors or [],
        skse_errors=req.skse_errors or [],
        response_language=req.response_language or "auto",
        include_web_search=req.include_web_search if req.include_web_search is not None else True,
        file_investigation_summary=req.file_investigation_summary,
    )
    return result
