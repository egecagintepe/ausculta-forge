"""AuscultaForge — Local Desktop Application FastAPI & WebSocket Server.

Provides the local bridge between Python's pcg_core signal processing pipeline
and the React frontend desktop client.
"""

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Optional
import time

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from pcg_core.recording import list_sessions, get_session, validate_session_id
from .state import StreamManager
from .protocol import (
    make_hello_message,
    make_stream_state_message,
    make_recording_state_message,
    make_error_message,
)


DEFAULT_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]


def create_app(
    sessions_dir: str | Path = "experiments/sessions",
    allowed_origins: Optional[list[str]] = None,
) -> FastAPI:
    manager = StreamManager(sessions_dir=sessions_dir)
    origins = list(allowed_origins) if allowed_origins is not None else list(DEFAULT_ALLOWED_ORIGINS)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Startup
        await manager.start_streaming_task()
        yield
        # Shutdown
        await manager.stop_streaming_task()

    app = FastAPI(
        title="AuscultaForge Local Desktop Bridge",
        version="1.0.0",
        lifespan=lifespan,
    )

    # Permit strictly local frontend origins (loopback only)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    # Store manager in state
    app.state.manager = manager

    # Request models
    class FilterRequest(BaseModel):
        preset: Optional[str] = None
        low_hz: Optional[float] = None
        high_hz: Optional[float] = None

    class SourceRequest(BaseModel):
        source_type: str
        path: Optional[str] = None
        session_id: Optional[str] = None

    class RecordingStartRequest(BaseModel):
        source: Optional[str] = None

    # REST Endpoints
    @app.get("/api/status")
    def get_status() -> dict[str, Any]:
        return {
            "capabilities": manager.get_capabilities(),
            "state": manager.get_state_dict(),
        }

    @app.get("/api/sessions")
    def api_list_sessions() -> list[dict[str, Any]]:
        return list_sessions(manager.sessions_dir)

    @app.get("/api/sessions/{session_id}")
    def api_get_session(session_id: str) -> dict[str, Any]:
        try:
            valid_id = validate_session_id(session_id, manager.sessions_dir)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid session ID")
        sess = get_session(valid_id, manager.sessions_dir)
        if not sess:
            raise HTTPException(status_code=404, detail="Session not found")
        return sess

    @app.post("/api/sessions/{session_id}/replay")
    async def api_replay_session(session_id: str) -> dict[str, Any]:
        try:
            valid_id = validate_session_id(session_id, manager.sessions_dir)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid session ID")
        sess = get_session(valid_id, manager.sessions_dir)
        if not sess:
            raise HTTPException(status_code=404, detail="Session not found")
        try:
            new_state = manager.select_source("session", session_id=valid_id)
        except (ValueError, FileNotFoundError) as e:
            raise HTTPException(status_code=400, detail=str(e))
        manager.start_stream()
        await manager.broadcast(make_stream_state_message(new_state))
        return {"status": "replaying", "session_id": valid_id, "state": new_state}

    @app.post("/api/stream/start")
    async def api_start_stream() -> dict[str, Any]:
        manager.start_stream()
        st = manager.get_state_dict()
        await manager.broadcast(make_stream_state_message(st))
        return st

    @app.post("/api/stream/pause")
    async def api_pause_stream() -> dict[str, Any]:
        manager.pause_stream()
        st = manager.get_state_dict()
        await manager.broadcast(make_stream_state_message(st))
        return st

    @app.post("/api/stream/stop")
    async def api_stop_stream() -> dict[str, Any]:
        manager.stop_stream()
        st = manager.get_state_dict()
        await manager.broadcast(make_stream_state_message(st))
        return st

    @app.post("/api/stream/filter")
    async def api_set_filter(req: FilterRequest) -> dict[str, Any]:
        st = manager.set_filter(preset=req.preset, low_hz=req.low_hz, high_hz=req.high_hz)
        await manager.broadcast(make_stream_state_message(st))
        return st

    @app.post("/api/stream/source")
    async def api_set_source(req: SourceRequest) -> dict[str, Any]:
        st = manager.select_source(req.source_type, path=req.path, session_id=req.session_id)
        await manager.broadcast(make_stream_state_message(st))
        return st

    @app.post("/api/recording/start")
    async def api_start_recording(req: RecordingStartRequest) -> dict[str, Any]:
        sid = manager.start_recording(source_label=req.source)
        rec_msg = make_recording_state_message(
            is_recording=True,
            session_id=sid,
            elapsed_seconds=0.0,
            samples_recorded=0,
            blocks_recorded=0,
            source=manager.active_source_name,
            sample_rate_hz=manager.sample_rate_hz,
        )
        await manager.broadcast(rec_msg)
        return {"session_id": sid, "status": "recording_started"}

    @app.post("/api/recording/stop")
    async def api_stop_recording() -> dict[str, Any]:
        meta = manager.stop_recording()
        rec_msg = make_recording_state_message(
            is_recording=False,
            session_id=meta.session_id,
            elapsed_seconds=meta.duration_s,
            samples_recorded=meta.total_samples,
            blocks_recorded=meta.total_blocks,
            source=meta.source,
            sample_rate_hz=meta.sample_rate_hz,
        )
        await manager.broadcast(rec_msg)
        return meta.to_dict()

    # WebSocket Real-Time Ingestion & Command Endpoint
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        origin = websocket.headers.get("origin")
        # Validate WebSocket Origin if present (allows test clients/headless tools while guarding browsers)
        if origin and origin not in origins:
            await websocket.close(code=1008)  # 1008: Policy Violation
            return

        await websocket.accept()
        manager.register_client(websocket)

        try:
            # Send initial hello & state message
            hello = make_hello_message(
                capabilities=manager.get_capabilities(),
                state=manager.get_state_dict(),
            )
            await websocket.send_json(hello)

            while True:
                data = await websocket.receive_json()
                action = data.get("action") or data.get("type")

                if action in ("start_stream", "resume_stream"):
                    manager.start_stream()
                    await manager.broadcast(make_stream_state_message(manager.get_state_dict()))

                elif action == "pause_stream":
                    manager.pause_stream()
                    await manager.broadcast(make_stream_state_message(manager.get_state_dict()))

                elif action == "stop_stream":
                    manager.stop_stream()
                    await manager.broadcast(make_stream_state_message(manager.get_state_dict()))

                elif action == "set_filter":
                    preset = data.get("preset")
                    low_hz = data.get("low_hz")
                    high_hz = data.get("high_hz")
                    st = manager.set_filter(preset=preset, low_hz=low_hz, high_hz=high_hz)
                    await manager.broadcast(make_stream_state_message(st))

                elif action == "select_source":
                    st = manager.select_source(
                        source_type=data.get("source_type", "mock"),
                        path=data.get("path"),
                        session_id=data.get("session_id"),
                    )
                    await manager.broadcast(make_stream_state_message(st))

                elif action == "start_recording":
                    source_label = data.get("source")
                    sid = manager.start_recording(source_label=source_label)
                    rec_msg = make_recording_state_message(
                        is_recording=True,
                        session_id=sid,
                        elapsed_seconds=0.0,
                        samples_recorded=0,
                        blocks_recorded=0,
                        source=manager.active_source_name,
                        sample_rate_hz=manager.sample_rate_hz,
                    )
                    await manager.broadcast(rec_msg)

                elif action == "stop_recording":
                    try:
                        meta = manager.stop_recording()
                        rec_msg = make_recording_state_message(
                            is_recording=False,
                            session_id=meta.session_id,
                            elapsed_seconds=meta.duration_s,
                            samples_recorded=meta.total_samples,
                            blocks_recorded=meta.total_blocks,
                            source=meta.source,
                            sample_rate_hz=meta.sample_rate_hz,
                        )
                        await manager.broadcast(rec_msg)
                    except Exception as e:
                        await websocket.send_json(make_error_message(str(e), "RECORDING_STOP_FAILED"))

                elif action == "ping":
                    await websocket.send_json({"type": "pong", "time": time.time()})

        except WebSocketDisconnect:
            pass
        finally:
            manager.unregister_client(websocket)

    return app
