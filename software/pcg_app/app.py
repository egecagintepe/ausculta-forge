"""AuscultaForge — Local Desktop Application FastAPI & WebSocket Server.

Provides the local bridge between Python's pcg_core signal processing pipeline,
device runtime foundation, and the React frontend desktop client.
"""

from contextlib import asynccontextmanager
import json
from pathlib import Path
from typing import Any, Optional
import time

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, File, UploadFile, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from pcg_core.recording import list_sessions, get_session, validate_session_id
from pcg_core.scientific import SystemIdConfig
from pcg_core.scientific_config import list_analysis_profiles
from .state import StreamManager
from .device_runtime import DeviceRuntime
from .analysis_service import AnalysisService
from .protocol import (
    make_hello_message,
    make_stream_state_message,
    make_recording_state_message,
    make_device_state_message,
    make_device_event_message,
    make_device_stats_message,
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
    device_runtime: Optional[DeviceRuntime] = None,
    assets_dir: str | Path = "experiments/analysis-assets",
    analysis_dir: str | Path = "experiments/analysis",
    analysis_service: Optional[AnalysisService] = None,
) -> FastAPI:
    manager = StreamManager(sessions_dir=sessions_dir, device_runtime=device_runtime)
    analysis = analysis_service or AnalysisService(
        assets_dir=assets_dir,
        analysis_dir=analysis_dir,
        sessions_dir=sessions_dir,
    )
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
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # Store manager and analysis service in state
    app.state.manager = manager
    app.state.analysis = analysis

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

    class CompareRequest(BaseModel):
        asset_id: str
        session_id: str
        max_points: Optional[int] = 600

    class ScientificAnalyzeRequest(BaseModel):
        profile_id: Optional[str] = "GENERAL_PCG_V1"
        welch_nperseg: Optional[int] = 2048
        welch_noverlap: Optional[int] = None
        max_display_points: Optional[int] = 600

    class SystemIdRequest(BaseModel):
        asset_id: str
        session_id: str
        nperseg: Optional[int] = 1024
        noverlap: Optional[int] = 512
        window: Optional[str] = "hann"
        excited_band_min_hz: Optional[float] = 20.0
        excited_band_max_hz: Optional[float] = 1000.0
        energy_threshold_db_rel_max: Optional[float] = -30.0
        max_display_points: Optional[int] = 300

    class SegmentationSegmentRequest(BaseModel):
        session_id: str
        model_id: Optional[str] = None
        profile_id: Optional[str] = "SPRINGER_PHYSIONET_REFERENCE_V1"
        max_display_points: Optional[int] = 600

    # REST Endpoints
    @app.get("/api/status")
    def get_status() -> dict[str, Any]:
        return {
            "capabilities": manager.get_capabilities(),
            "state": manager.get_state_dict(),
            "device": manager.device_runtime.get_state_dict(),
        }

    @app.get("/api/device/state")
    def get_device_state() -> dict[str, Any]:
        return manager.device_runtime.get_state_dict()

    @app.get("/api/device/events")
    def get_device_events(limit: int = 50) -> list[dict[str, Any]]:
        return manager.device_runtime.event_log.get_recent(limit=limit)

    @app.get("/api/device/stats")
    def get_device_stats() -> dict[str, Any]:
        return manager.device_runtime.stats.to_dict()

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

    @app.get("/api/sessions/{session_id}/analysis-summary")
    def api_get_session_analysis_summary(session_id: str, max_points: int = 600) -> dict[str, Any]:
        try:
            return analysis.get_session_analysis_summary(session_id, max_waveform_points=max_points)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))

    # Reference Asset Endpoints
    @app.post("/api/analysis/assets", status_code=201)
    async def api_upload_reference_asset(file: UploadFile = File(...)) -> dict[str, Any]:
        try:
            content = await file.read()
            return analysis.import_reference_wav(content, original_filename=file.filename or "reference.wav")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to process reference audio: {e}")

    @app.get("/api/analysis/assets")
    def api_list_reference_assets() -> list[dict[str, Any]]:
        return analysis.list_reference_assets()

    @app.get("/api/analysis/assets/{asset_id}")
    def api_get_reference_asset(asset_id: str) -> dict[str, Any]:
        asset = analysis.get_reference_asset(asset_id)
        if not asset:
            raise HTTPException(status_code=404, detail=f"Reference asset not found: {asset_id}")
        return asset

    @app.delete("/api/analysis/assets/{asset_id}")
    def api_delete_reference_asset(asset_id: str) -> dict[str, Any]:
        try:
            removed = analysis.delete_reference_asset(asset_id)
            if not removed:
                raise HTTPException(status_code=404, detail=f"Reference asset not found: {asset_id}")
            return {"status": "deleted", "asset_id": asset_id}
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    # Comparison Workbench Endpoints
    @app.post("/api/analysis/compare")
    def api_compare_reference_and_capture(req: CompareRequest) -> dict[str, Any]:
        try:
            return analysis.compare_reference_and_capture(
                asset_id=req.asset_id,
                session_id=req.session_id,
                max_waveform_points=req.max_points or 600,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @app.get("/api/analysis/reports")
    def api_list_comparison_reports() -> list[dict[str, Any]]:
        return analysis.list_comparison_reports()

    @app.get("/api/analysis/{analysis_id}")
    def api_get_comparison_report(analysis_id: str) -> dict[str, Any]:
        try:
            report = analysis.get_comparison_report(analysis_id)
            if not report:
                raise HTTPException(status_code=404, detail=f"Comparison report not found: {analysis_id}")
            return report
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.get("/api/analysis/{analysis_id}/export")
    def api_export_comparison_report(analysis_id: str) -> Response:
        try:
            report = analysis.get_comparison_report(analysis_id)
            if not report:
                raise HTTPException(status_code=404, detail=f"Comparison report not found: {analysis_id}")
            content = json.dumps(report, indent=2)
            filename = f"comparison_{analysis_id}.json"
            return Response(
                content=content,
                media_type="application/json",
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}"'
                },
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    # Scientific Analysis & System Identification Endpoints
    @app.get("/api/scientific/profiles")
    def api_list_scientific_profiles() -> list[dict[str, Any]]:
        return [p.to_dict() for p in list_analysis_profiles()]

    @app.post("/api/scientific/session/{session_id}/analyze")
    def api_analyze_session_scientific(
        session_id: str,
        req: Optional[ScientificAnalyzeRequest] = None,
    ) -> dict[str, Any]:
        payload = req or ScientificAnalyzeRequest()
        try:
            return analysis.analyze_session_scientific(
                session_id=session_id,
                profile_id=payload.profile_id or "GENERAL_PCG_V1",
                welch_nperseg=payload.welch_nperseg or 2048,
                welch_noverlap=payload.welch_noverlap,
                max_display_points=payload.max_display_points or 600,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @app.post("/api/scientific/system-id")
    def api_run_system_id(req: SystemIdRequest) -> dict[str, Any]:
        cfg = SystemIdConfig(
            nperseg=req.nperseg or 1024,
            noverlap=req.noverlap,
            window=req.window or "hann",
            excited_band_hz=(req.excited_band_min_hz or 20.0, req.excited_band_max_hz or 1000.0),
            energy_threshold_db_rel_max=req.energy_threshold_db_rel_max if req.energy_threshold_db_rel_max is not None else -30.0,
        )
        try:
            return analysis.run_system_id(
                asset_id=req.asset_id,
                session_id=req.session_id,
                config=cfg,
                max_display_points=req.max_display_points or 300,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @app.get("/api/scientific/system-id/reports")
    def api_list_system_id_reports() -> list[dict[str, Any]]:
        return analysis.list_system_id_reports()

    @app.get("/api/scientific/system-id/{analysis_id}")
    def api_get_system_id_report(analysis_id: str) -> dict[str, Any]:
        try:
            report = analysis.get_system_id_report(analysis_id)
            if not report:
                raise HTTPException(status_code=404, detail=f"System identification report not found: {analysis_id}")
            return report
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    # =========================================================================
    # Springer LR-HSMM Segmentation Endpoints
    # =========================================================================

    @app.get("/api/scientific/segmentation/models")
    def api_list_segmentation_models() -> list[dict[str, Any]]:
        return analysis.list_segmentation_models()

    @app.post("/api/scientific/segmentation/segment")
    def api_segment_session(req: SegmentationSegmentRequest) -> dict[str, Any]:
        try:
            return analysis.run_segmentation(
                session_id=req.session_id,
                model_id=req.model_id,
                profile_id=req.profile_id or "SPRINGER_PHYSIONET_REFERENCE_V1",
                max_display_points=req.max_display_points or 600,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @app.get("/api/scientific/segmentation/reports")
    def api_list_segmentation_reports() -> list[dict[str, Any]]:
        return analysis.list_segmentation_reports()

    @app.get("/api/scientific/segmentation/{analysis_id}")
    def api_get_segmentation_report(analysis_id: str) -> dict[str, Any]:
        try:
            report = analysis.get_segmentation_report(analysis_id)
            if not report:
                raise HTTPException(status_code=404, detail=f"Segmentation report not found: {analysis_id}")
            return report
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.get("/api/scientific/validation/benchmarks")
    def api_list_validation_benchmarks() -> list[dict[str, Any]]:
        return analysis.list_validation_benchmarks()

    @app.get("/api/scientific/validation/benchmarks/{benchmark_id}")
    def api_get_validation_benchmark(benchmark_id: str) -> dict[str, Any]:
        try:
            report = analysis.get_validation_benchmark(benchmark_id)
            if not report:
                raise HTTPException(status_code=404, detail=f"Validation benchmark not found: {benchmark_id}")
            return report
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

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
        try:
            st = manager.select_source(req.source_type, path=req.path, session_id=req.session_id)
        except (ValueError, FileNotFoundError) as e:
            raise HTTPException(status_code=400, detail=str(e))
        await manager.broadcast(make_stream_state_message(st))
        return st

    @app.post("/api/recording/start")
    async def api_start_recording(req: RecordingStartRequest) -> dict[str, Any]:
        try:
            sid = manager.start_recording(source_label=req.source)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

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
                device_state=manager.device_runtime.get_state_dict(),
            )
            await websocket.send_json(hello)
            await websocket.send_json(make_device_state_message(manager.device_runtime.get_state_dict()))

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
                    try:
                        st = manager.select_source(
                            source_type=data.get("source_type", "none"),
                            path=data.get("path"),
                            session_id=data.get("session_id"),
                        )
                        await manager.broadcast(make_stream_state_message(st))
                    except Exception as e:
                        await websocket.send_json(make_error_message(str(e), "SOURCE_SELECTION_FAILED"))

                elif action == "start_recording":
                    try:
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
                    except Exception as e:
                        await websocket.send_json(make_error_message(str(e), "RECORDING_START_FAILED"))

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

                elif action == "get_device_state":
                    await websocket.send_json(make_device_state_message(manager.device_runtime.get_state_dict()))

                elif action == "get_device_stats":
                    await websocket.send_json(make_device_stats_message(manager.device_runtime.stats.to_dict()))

                elif action == "get_device_events":
                    limit = data.get("limit", 50)
                    events = manager.device_runtime.event_log.get_recent(limit=limit)
                    await websocket.send_json({"type": "device_events", "events": events})

                elif action == "ping":
                    await websocket.send_json({"type": "pong", "time": time.time()})

        except WebSocketDisconnect:
            pass
        finally:
            manager.unregister_client(websocket)

    return app
