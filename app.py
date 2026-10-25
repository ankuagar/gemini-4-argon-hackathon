"""
app.py
FastAPI server and REST API for ArgonLedger — Million-Token Codebase Migration & Verification Engine.
"""
from __future__ import annotations

import asyncio
import base64
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from engine.migrator import BENCHMARK_SPECS, MigrationOrchestrator, ROOT_DIR
from engine.world_loop import REAL_VIDEOS_DIR, WorldLoopOrchestrator


app = FastAPI(
    title="ArgonLedger — Gemini 4 Argon Whole-Repo Migration & 3D World Video Verification Engine",
    version="1.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

orchestrator = MigrationOrchestrator()
world_orchestrator = WorldLoopOrchestrator(orchestrator.client)
STATIC_DIR = ROOT_DIR / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class CreateSessionRequest(BaseModel):
    benchmark_id: str
    thinking_level: str = "medium"
    use_long_decode_background: bool = False


class ApproveLedgerRequest(BaseModel):
    ledger: Optional[Dict[str, Any]] = None


class CustomBenchmarkRequest(BaseModel):
    benchmark_id: str
    title: str
    subtitle: str = "Custom Open-Source Repository / Subsystem Migration"
    persona: str = "Open-Source Subsystem Maintainer"
    pain_point: str = "Cross-module architectural refactoring with strict compiler & test verification."
    reference_link: str = "https://github.com/"
    source_dir: str
    mutable_files: List[str]
    readonly_context_files: List[str] = []
    language: str = "c"
    task_instructions: str
    verify_cmd: str
    forbidden_patterns: List[str] = []


OPEN_SOURCE_CRISIS_CATALOG: List[Dict[str, Any]] = [
    {
        "ecosystem": "Linux Kernel (Memory Safety, Stack Leaks & `get_cycles` Purge)",
        "scale": "40M+ LoC C Subsystem",
        "challenge": "Zeroing kernel-to-userspace struct alignment padding (`0xAA` stack leak), replacing `strcpy()` with bounded `kobj_strscpy()`, purging fake `get_cycles()`, and enforcing checked overflow arithmetic.",
        "built_in_benchmark": "linux_git_c_hardening",
        "frontpage_card_label": "Frontpage Card #3 (linux_git_c_hardening)",
        "custom_slug": "linux_kernel_uapi_hardening",
        "links": [
            "https://www.youtube.com/watch?v=g9TEuezEm9c&t=38",
            "https://pdos.csail.mit.edu/papers/chen-kbugs.pdf",
            "https://gist.github.com/andy-shev/a2cb1ee4767d6d2f5d20db53ecb9aabc",
        ],
    },
    {
        "ecosystem": "Git Core VCS (SHA-1 → SHA-256 Transition & Global State Removal)",
        "scale": "30-year C Codebase",
        "challenge": "Eliminating file-scoped mutable state (`the_repo_hash_ctx`) and hardcoded 20-byte SHA-1 assumptions to make object formatting reentrant and cryptographically agile (20B SHA-1 + 32B SHA-256).",
        "built_in_benchmark": "linux_git_c_hardening",
        "frontpage_card_label": "Frontpage Card #3 (linux_git_c_hardening)",
        "custom_slug": "git_sha256_reentrant_oid",
        "links": ["https://git-scm.com/docs/hash-function-transition"],
    },
    {
        "ecosystem": "Ladybird & Rust-for-Linux (C/C++ Codec to 0-`unsafe` Safe Rust)",
        "scale": "C-to-Rust FFI & Codec Bridge",
        "challenge": "Porting legacy C binary codecs, RLE compression, and stateful streaming sessions into 100% safe Rust (`0 unsafe`, fallible `Result<T, CodecError>`) verified by a 107-check C-vs-Rust differential fuzzer.",
        "built_in_benchmark": "c_to_rust_framecodec",
        "frontpage_card_label": "Frontpage Card #2 (c_to_rust_framecodec)",
        "custom_slug": "ladybird_safe_rust_codec",
        "links": [
            "https://ladybird.org/",
            "https://www.youtube.com/watch?v=QqXopaeIHZs",
        ],
    },
    {
        "ecosystem": "Apache Superset Monorepo (TypeScript 6.0 Strict Upgrade)",
        "scale": "1,400+ TS/TSX Files",
        "challenge": "Enabling `strict: true`, `exactOptionalPropertyTypes`, `noUncheckedIndexedAccess`, and `verbatimModuleSyntax` across coupled `@superset-ui/*` packages without `any` escapes.",
        "built_in_benchmark": "superset_ts6",
        "frontpage_card_label": "Frontpage Card #1 (superset_ts6)",
        "custom_slug": "superset_ts6_strict_custom",
        "links": ["https://github.com/apache/superset/issues/39539"],
    },
    {
        "ecosystem": "Ray / Python Ecosystem (Drop Pydantic v1 & Strict Typing)",
        "scale": "Multi-Service Python Platform",
        "challenge": "Removing deprecated Pydantic v1 `@validator`, `@root_validator`, and `.dict()` shims across coupled services while enforcing `mypy --strict` and zero deprecation warnings.",
        "built_in_benchmark": "py_v1_to_v2",
        "frontpage_card_label": "Frontpage Card #4 (py_v1_to_v2)",
        "custom_slug": "ray_pydantic_v2_strict",
        "links": ["https://github.com/ray-project/ray/issues/58876"],
    },
]


@app.get("/", response_class=HTMLResponse)
async def serve_index() -> FileResponse:
    return FileResponse(str(STATIC_DIR / "index.html"))


@app.get("/api/benchmarks")
async def list_benchmarks() -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for bid, spec in BENCHMARK_SPECS.items():
        files_preview: List[Dict[str, Any]] = []
        for rel in spec.mutable_files:
            fp = spec.initial_dir / rel
            content = fp.read_text(encoding="utf-8") if fp.exists() else ""
            files_preview.append(
                {
                    "path": rel,
                    "role": "mutable",
                    "lines": len(content.splitlines()),
                    "content": content,
                }
            )
        for rel in spec.readonly_context_files:
            fp = spec.initial_dir / rel
            content = fp.read_text(encoding="utf-8") if fp.exists() else ""
            files_preview.append(
                {
                    "path": rel,
                    "role": "readonly_contract",
                    "lines": len(content.splitlines()),
                    "content": content,
                }
            )
        items.append(
            {
                "id": spec.id,
                "title": spec.title,
                "subtitle": spec.subtitle,
                "persona": spec.persona,
                "pain_point": spec.pain_point,
                "reference_link": spec.reference_link,
                "language": spec.language,
                "mutable_file_count": len(spec.mutable_files),
                "mutable_files": spec.mutable_files,
                "readonly_context_files": spec.readonly_context_files,
                "task_instructions": spec.task_instructions,
                "initial_dir": str(spec.initial_dir),
                "files": files_preview,
            }
        )
    return items


@app.get("/api/open-source-presets")
async def get_open_source_presets() -> List[Dict[str, Any]]:
    return OPEN_SOURCE_CRISIS_CATALOG


@app.get("/api/live-traffic")
async def get_live_traffic() -> Dict[str, Any]:
    calls = orchestrator.client.get_live_traffic(limit=30)
    in_flight = sum(1 for c in calls if c.get("status") == "IN_FLIGHT")
    return {
        "in_flight_count": in_flight,
        "total_calls": len(calls),
        "calls": calls,
    }


@app.post("/api/benchmarks/custom")
async def create_custom_benchmark(req: CustomBenchmarkRequest) -> Dict[str, Any]:
    try:
        spec = await asyncio.to_thread(
            orchestrator.register_custom_benchmark,
            benchmark_id=req.benchmark_id,
            title=req.title,
            subtitle=req.subtitle,
            persona=req.persona,
            pain_point=req.pain_point,
            reference_link=req.reference_link,
            source_dir=req.source_dir,
            mutable_files=req.mutable_files,
            readonly_context_files=req.readonly_context_files,
            language=req.language,
            task_instructions=req.task_instructions,
            verify_cmd=req.verify_cmd,
            forbidden_patterns=req.forbidden_patterns,
        )
        return {"status": "registered", "benchmark_id": spec.id}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/sessions")
async def create_session(req: CreateSessionRequest) -> Dict[str, Any]:
    try:
        session = await asyncio.to_thread(
            orchestrator.create_session,
            req.benchmark_id,
            req.thinking_level,
            req.use_long_decode_background,
        )
        return session.to_dict()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str) -> Dict[str, Any]:
    session = orchestrator.sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session.to_dict()


@app.post("/api/sessions/{session_id}/ledger")
async def generate_ledger(session_id: str) -> Dict[str, Any]:
    if session_id not in orchestrator.sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    try:
        session = await asyncio.to_thread(orchestrator.generate_ledger, session_id)
        return session.to_dict()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/sessions/{session_id}/approve")
async def approve_ledger(session_id: str, req: ApproveLedgerRequest) -> Dict[str, Any]:
    if session_id not in orchestrator.sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    session = await asyncio.to_thread(orchestrator.approve_ledger, session_id, req.ledger)
    return session.to_dict()


@app.post("/api/sessions/{session_id}/baseline")
async def run_baseline(session_id: str) -> Dict[str, Any]:
    if session_id not in orchestrator.sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    try:
        session = await asyncio.to_thread(orchestrator.run_baseline_file_by_file, session_id)
        return session.to_dict()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/sessions/{session_id}/argon")
async def run_argon(session_id: str) -> Dict[str, Any]:
    if session_id not in orchestrator.sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    try:
        session = await asyncio.to_thread(orchestrator.run_argon_migration, session_id)
        return session.to_dict()
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/docs")
async def get_project_docs() -> Dict[str, str]:
    agents_p = ROOT_DIR / "AGENTS.md"
    design_p = ROOT_DIR / "DESIGN.md"
    return {
        "agents_md": agents_p.read_text(encoding="utf-8") if agents_p.exists() else "",
        "design_md": design_p.read_text(encoding="utf-8") if design_p.exists() else "",
    }


@app.post("/api/sessions/{session_id}/commit")
async def commit_migration(session_id: str) -> Dict[str, Any]:
    try:
        return await asyncio.to_thread(orchestrator.commit_approved_migration, session_id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Track 2: 3D Procedural World & Game Render -> Watch Video -> Critique -> Fix Loop
# ---------------------------------------------------------------------------
class CreateTrack2SessionRequest(BaseModel):
    scenario_id: str = "real_bear_hike"
    custom_goal: Optional[str] = None
    thinking_level: str = "medium"


class Track2UploadVideoRequest(BaseModel):
    filename: str
    video_base64: str
    custom_goal: Optional[str] = None
    thinking_level: str = "medium"


class Track2CritiqueRequest(BaseModel):
    frames: List[str] = []
    telemetry: Dict[str, Any] = {}
    target_iteration: Optional[int] = None


class Track2FixRequest(BaseModel):
    custom_feedback: Optional[str] = None


@app.get("/api/track2/scenarios")
async def list_track2_scenarios() -> List[Dict[str, Any]]:
    return world_orchestrator.list_scenarios()


@app.get("/api/track2/real_videos/{filename}")
async def get_track2_real_video(filename: str) -> FileResponse:
    safe_name = Path(filename).name
    target = REAL_VIDEOS_DIR / safe_name
    if not target.exists():
        raise HTTPException(status_code=404, detail="Real video file not found")
    return FileResponse(target, media_type="video/mp4")


@app.post("/api/track2/upload_video")
async def upload_track2_real_video(req: Track2UploadVideoRequest) -> Dict[str, Any]:
    b64_part = req.video_base64.split(",", 1)[1] if "," in req.video_base64 else req.video_base64
    try:
        raw_bytes = base64.b64decode(b64_part)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid base64 video payload: {exc}") from exc

    sess = await asyncio.to_thread(
        world_orchestrator.create_session_from_uploaded_video,
        raw_bytes,
        req.filename,
        req.custom_goal,
        req.thinking_level,
    )
    return sess.to_dict()


@app.post("/api/track2/sessions")
async def create_track2_session(req: CreateTrack2SessionRequest) -> Dict[str, Any]:
    sess = await asyncio.to_thread(
        world_orchestrator.create_session,
        req.scenario_id,
        req.custom_goal,
        req.thinking_level,
    )
    return sess.to_dict()


@app.get("/api/track2/sessions/{session_id}")
async def get_track2_session(session_id: str) -> Dict[str, Any]:
    sess = world_orchestrator.sessions.get(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Track 2 session not found")
    return sess.to_dict()


@app.get("/api/track2/sessions/{session_id}/artifacts.zip")
async def download_track2_artifacts_zip(session_id: str) -> Response:
    if session_id not in world_orchestrator.sessions:
        raise HTTPException(status_code=404, detail="Track 2 session not found")
    zip_bytes = await asyncio.to_thread(world_orchestrator.build_artifacts_zip, session_id)
    sess = world_orchestrator.sessions[session_id]
    fname = f"argon_real2sim_{sess.scenario_id}_{session_id}.zip"
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


@app.post("/api/track2/sessions/{session_id}/critique")
async def critique_track2_video(session_id: str, req: Track2CritiqueRequest) -> Dict[str, Any]:
    if session_id not in world_orchestrator.sessions:
        raise HTTPException(status_code=404, detail="Track 2 session not found")
    try:
        sess = await asyncio.to_thread(
            world_orchestrator.critique_iteration_video,
            session_id,
            req.frames,
            req.telemetry,
            req.target_iteration,
        )
        return sess.to_dict()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/track2/sessions/{session_id}/fix")
async def fix_track2_world(session_id: str, req: Track2FixRequest) -> Dict[str, Any]:
    if session_id not in world_orchestrator.sessions:
        raise HTTPException(status_code=404, detail="Track 2 session not found")
    try:
        sess = await asyncio.to_thread(
            world_orchestrator.fix_and_upgrade_world,
            session_id,
            req.custom_feedback,
        )
        return sess.to_dict()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/track2/sessions/{session_id}/video/{iteration}")
async def get_track2_video(session_id: str, iteration: int) -> FileResponse:
    sess = world_orchestrator.sessions.get(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Track 2 session not found")
    for it in sess.iterations:
        if it.iteration == iteration and it.video_path and Path(it.video_path).exists():
            return FileResponse(it.video_path, media_type="video/mp4")
    raise HTTPException(status_code=404, detail="Recorded video not found for this iteration")


class Track2SwitchTakeRequest(BaseModel):
    filename: str


@app.post("/api/track2/sessions/{session_id}/switch_take")
async def switch_track2_video_take(session_id: str, req: Track2SwitchTakeRequest) -> Dict[str, Any]:
    if session_id not in world_orchestrator.sessions:
        raise HTTPException(status_code=404, detail="Track 2 session not found")
    sess = world_orchestrator.switch_video_take(session_id, req.filename)
    return sess.to_dict()


