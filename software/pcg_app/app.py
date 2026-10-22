"""AuscultaForge — Local Desktop Application FastAPI & WebSocket Server.

Provides the local bridge between Python's pcg_core signal processing pipeline,
device runtime foundation, and the React frontend desktop client.
"""

import asyncio
from contextlib import asynccontextmanager
import json
from pathlib import Path
from typing import Any, Optional
import time

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, File, UploadFile, Response
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from pcg_core.recording import (
    list_sessions,
    get_session,
    validate_session_id,
    verify_session_integrity,
    export_session_manifest,
    delete_session,
    SessionCorruptedError,
)
from pcg_core.scientific import SystemIdConfig
from pcg_core.scientific_config import list_analysis_profiles
from .state import StreamManager
from .device_runtime import DeviceRuntime, DeviceState
from .analysis_service import AnalysisService
from .virtual_bench import VirtualBenchRunner
from .protocol import (
    make_hello_message,
    make_stream_state_message,
    make_recording_state_message,
    make_device_state_message,
    make_device_event_message,
    make_device_stats_message,
    make_error_message,
)
from .diagnostics.fault_catalog import list_all_faults, get_fault_definition
from .diagnostics.event_model import DiagnosticEvent, Severity, Subsystem, EvidenceOrigin
from .diagnostics.flight_recorder import get_flight_recorder
from .diagnostics.usb_doctor import UsbDiscoveryDoctor
from .diagnostics.correlation_engine import RootCauseCorrelationEngine
from .diagnostics.support_bundle import DiagnosticsSupportBundleExporter
from .diagnostics.fault_injection_lab import FaultInjectionLab
from .ml import (
    ResearchModelRegistry,
    ResearchInferenceService,
    AudioValidationError,
    SubjectIntegrityError,
    UnauthorizedPathError,
    ModelUnavailableError,
)

DEFAULT_ALLOWED_ORIGINS = [

    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "tauri://localhost",
    "https://tauri.localhost",
    "http://tauri.localhost",
]


def create_app(
    sessions_dir: str | Path = "experiments/sessions",
    allowed_origins: Optional[list[str]] = None,
    device_runtime: Optional[DeviceRuntime] = None,
    assets_dir: str | Path = "experiments/analysis-assets",
    analysis_dir: str | Path = "experiments/analysis",
    analysis_service: Optional[AnalysisService] = None,
    auth_token: Optional[str] = None,
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
    app.state.stream_manager = manager
    app.state.analysis_service = analysis

    # Permit strictly local frontend origins (loopback only)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    if auth_token:
        from starlette.middleware.base import BaseHTTPMiddleware
        from starlette.responses import JSONResponse

        class DesktopAuthMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request, call_next):
                if request.method == "OPTIONS" or request.url.path in (
                    "/api/health",
                    "/docs",
                    "/openapi.json",
                    "/favicon.ico",
                ):
                    return await call_next(request)

                header_token = request.headers.get("X-AuscultaForge-Auth")
                if not header_token:
                    auth_header = request.headers.get("Authorization", "")
                    if auth_header.startswith("Bearer "):
                        header_token = auth_header[7:]

                if header_token != auth_token:
                    return JSONResponse(
                        status_code=403,
                        content={
                            "detail": "Unauthorized: Invalid or missing AuscultaForge desktop authentication token"
                        },
                    )
                return await call_next(request)

        app.add_middleware(DesktopAuthMiddleware)

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

    class BenchRunRequest(BaseModel):
        scenario_id: Optional[str] = "all"
        seed: Optional[int] = 42

    class PhantomStimulusGenerateRequest(BaseModel):
        stimulus_type: str
        duration_s: Optional[float] = 5.0
        sample_rate_hz: Optional[int] = 48000
        amplitude_fs: Optional[float] = 0.8
        save_as_asset: Optional[bool] = True
        custom_params: Optional[dict[str, Any]] = None

    class PhantomCharacterizeRequest(BaseModel):
        asset_id: str
        session_id: str
        template_id: Optional[str] = "PHANTOM_LOG_SWEEP_20_500HZ_V1"
        trial_id: Optional[str] = None
        output_gain_dbfs: Optional[float] = -6.0
        operator_notes: Optional[str] = ""
        hardware_status: Optional[str] = "PENDING_PHYSICAL_MEASUREMENT"
        pipeline_buffer_delay_ms: Optional[float] = 30.0
        max_display_points: Optional[int] = 300

    class MetrologyRunRequest(BaseModel):
        config: dict[str, Any]

    class FaultInjectRequest(BaseModel):
        scenario_id: str

    class FaultResolveRequest(BaseModel):
        fault_code: str
        resolution_message: Optional[str] = None

    class UsbConnectRequest(BaseModel):
        port: str
        baudrate: Optional[int] = 115200
        timeout_s: Optional[float] = 3.0

    class UsbStartRequest(BaseModel):
        source_mode: Optional[int] = 1
        target_samples: Optional[int] = 480000
        sample_rate_hz: Optional[int] = 48000
        encoding: Optional[int] = 1
        channels: Optional[int] = 1
        timeout_s: Optional[float] = 3.0

    class ResearchPredictRequest(BaseModel):
        file_paths: list[str] = Field(..., min_length=1, max_length=4, description="1 to 4 PCG WAV recordings belonging to the patient")
        model_id: Optional[str] = Field(default="af_murmur_mil_1.0", description="ID of the research model")
        patient_identifier: Optional[str] = Field(default=None, description="Optional patient/subject identifier")
        same_subject_attestation: Optional[bool] = Field(default=False, description="User attestation that all recordings belong to the same person")



    # REST Endpoints
    @app.get("/api/health")
    def get_health() -> dict[str, Any]:
        return {
            "status": "ok",
            "app": "AuscultaForge",
            "version": "0.1.0-alpha.1",
        }

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

    @app.post("/api/device/poll")
    async def api_poll_device() -> dict[str, Any]:
        candidates = manager.device_runtime.discovery_provider.poll_candidates()
        manager.device_runtime.event_log.log(
            "DEVICE_SCAN_EXECUTED",
            f"Hardware discovery scan executed ({len(candidates)} candidate devices detected)",
            severity="info",
            metadata={"candidate_count": len(candidates)},
        )
        st = manager.device_runtime.get_state_dict()
        await manager.broadcast(make_device_state_message(st))
        return {
            "candidates": [c.to_dict() for c in candidates],
            "state": st,
        }

    @app.post("/api/device/disconnect")
    async def api_disconnect_device() -> dict[str, Any]:
        if manager.device_runtime.state in (DeviceState.READY, DeviceState.STREAMING):
            manager.handle_device_disconnect("User requested device disconnect via API")
            await manager.broadcast(make_device_state_message(manager.device_runtime.get_state_dict()))
        return manager.device_runtime.get_state_dict()

    # Authoritative Production USB CDC-ACM Device Endpoints
    @app.get("/api/device/usb/ports")
    def api_get_usb_ports() -> list[dict[str, Any]]:
        doctor = UsbDiscoveryDoctor()
        ports = doctor.scan_ports()
        result = [p.to_dict() for p in ports]
        result.append({
            "port_name": "SIMULATED_ESP32_S3",
            "description": "Simulated ESP32-S3 Endpoint (Loopback CI)",
            "hwid": "VIRTUAL_LOOPBACK_ENDPOINT",
            "vid_hex": "0x303A",
            "pid_hex": "0x0002",
            "is_espressif_candidate": True,
            "candidate_reason": "In-memory canonical hardware simulator (Deterministic G1 & Acoustic)",
        })
        return result

    @app.post("/api/device/usb/connect")
    async def api_connect_usb_device(req: UsbConnectRequest) -> dict[str, Any]:
        from .canonical.engine import CanonicalSessionEngine
        from .device_runtime import DeviceCapabilities, DeviceSamplePacket
        from .diagnostics.flight_recorder import get_flight_recorder

        # If an engine is currently running, disconnect it first
        if manager.device_runtime.canonical_engine and manager.device_runtime.canonical_engine.is_running:
            try:
                manager.device_runtime.canonical_engine.disconnect(timeout_s=1.0).result(timeout=1.0)
            except Exception:
                pass

        loop = asyncio.get_running_loop()

        def _on_audio(pkt):
            dsp = DeviceSamplePacket(
                sequence=pkt.sequence_id,
                timestamp_s=float(pkt.timestamp_us) / 1_000_000.0,
                raw_samples=pkt.raw_samples,
                flags=pkt.flags,
                crc_ok=pkt.crc_ok,
                meaningful_bits=24,
                sample_rate_hz=pkt.sample_rate_hz or 48000,
            )
            manager.ingest_device_packet_sync(dsp)

        def _on_disc(reason: str):
            manager.handle_device_disconnect(reason)
            st = manager.device_runtime.get_state_dict()
            try:
                loop = asyncio.get_running_loop()
                if loop.is_running():
                    asyncio.run_coroutine_threadsafe(manager.broadcast(make_device_state_message(st)), loop)
            except Exception:
                pass

        engine = CanonicalSessionEngine(
            diagnostic_journal=get_flight_recorder(),
            on_audio_packet=_on_audio,
            on_disconnect=_on_disc,
        )
        manager.device_runtime.canonical_engine = engine

        # Authoritative device lifecycle transition: ABSENT -> DETECTED -> OPENING
        if manager.device_runtime.state == DeviceState.ABSENT:
            manager.device_runtime.transition_to(DeviceState.DETECTED)
        if manager.device_runtime.state in (DeviceState.DETECTED, DeviceState.INTERRUPTED, DeviceState.ERROR):
            manager.device_runtime.transition_to(DeviceState.OPENING)

        try:
            fut = engine.connect(
                port=req.port,
                baudrate=req.baudrate or 115200,
                timeout_s=req.timeout_s or 3.0,
            )
            caps_ack = await asyncio.wrap_future(fut)
        except Exception as e:
            if manager.device_runtime.state == DeviceState.OPENING:
                manager.device_runtime.transition_to(DeviceState.ERROR, error_msg=str(e))
            else:
                manager.device_runtime._last_error = str(e)
                manager.device_runtime._state = DeviceState.ERROR
            st = manager.device_runtime.get_state_dict()
            await manager.broadcast(make_device_state_message(st))
            raise HTTPException(status_code=400, detail=f"Failed to connect to '{req.port}': {e}")

        # Authoritative lifecycle transition: OPENING -> HANDSHAKING -> READY
        manager.device_runtime.transition_to(DeviceState.HANDSHAKING)

        # Update DeviceRuntime state & capabilities
        fw_ver = f"{caps_ack.firmware_version_major}.{caps_ack.firmware_version_minor}.{caps_ack.firmware_version_patch}"
        dev_id = f"ESP32-S3 (UID: 0x{caps_ack.device_uid_low:08x})" if not engine.is_simulated else "Simulated ESP32-S3"
        dev_caps = DeviceCapabilities(
            protocol_version="1.0",
            firmware_version=fw_ver,
            device_id=dev_id,
            sample_rate_hz=caps_ack.hardware_sample_rate_hz,
            sample_format="signed_pcm",
            channels=1,
            max_block_size=caps_ack.max_frame_samples,
            sample_container_bits=32,
            meaningful_data_bits=24,
        )
        manager.device_runtime._capabilities = dev_caps
        manager.device_runtime.transition_to(DeviceState.READY)
        manager.device_runtime.event_log.log(
            "DEVICE_CONNECTED",
            f"Connected to {dev_id} on {req.port} (FW {fw_ver})",
            severity="info",
            metadata={"port": req.port, "is_simulated": engine.is_simulated},
        )
        st = manager.device_runtime.get_state_dict()
        await manager.broadcast(make_device_state_message(st))

        return {
            "status": "connected",
            "port": req.port,
            "capabilities": dev_caps.to_dict(),
            "summary": engine.get_summary(),
        }

    @app.post("/api/device/usb/start")
    async def api_start_usb_acquisition(req: Optional[UsbStartRequest] = None) -> dict[str, Any]:
        engine = manager.device_runtime.canonical_engine
        if not engine or not engine.is_running or engine.state.value != "READY":
            raise HTTPException(status_code=400, detail="Device is not ready for acquisition. Connect and verify HELLO first.")

        p = req or UsbStartRequest()
        src_mode = p.source_mode if p.source_mode is not None else 1
        tgt_samples = p.target_samples if p.target_samples is not None else 480000
        rate = p.sample_rate_hz or 48000

        try:
            fut = engine.start_acquisition(
                target_samples=tgt_samples,
                source_mode=src_mode,
                sample_rate_hz=rate,
                encoding=p.encoding or 1,
                channels=p.channels or 1,
                timeout_s=p.timeout_s or 3.0,
            )
            ack = await asyncio.wrap_future(fut)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to start acquisition: {e}")

        # Switch StreamManager to hardware source
        manager.source_type = "hardware"
        manager.active_source_name = f"Hardware: {engine.port_name}"
        manager.is_streaming = True
        manager.is_paused = False
        manager.sample_rate_hz = rate
        manager.device_runtime._state = DeviceState.STREAMING

        st = manager.device_runtime.get_state_dict()
        await manager.broadcast(make_device_state_message(st))
        await manager.broadcast(make_stream_state_message(manager.get_state_dict()))

        return {
            "status": "streaming",
            "session_id": f"0x{ack.session_id:08x}",
            "source_mode": src_mode,
            "target_samples": tgt_samples,
            "summary": engine.get_summary(),
        }

    @app.post("/api/device/usb/stop")
    async def api_stop_usb_acquisition() -> dict[str, Any]:
        engine = manager.device_runtime.canonical_engine
        if not engine or not engine.is_running:
            raise HTTPException(status_code=400, detail="No active device engine running.")

        try:
            fut = engine.stop_acquisition(timeout_s=4.0)
            telem = await asyncio.wrap_future(fut)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to stop acquisition: {e}")

        manager.device_runtime._state = DeviceState.READY
        manager.is_streaming = False
        st = manager.device_runtime.get_state_dict()
        await manager.broadcast(make_device_state_message(st))
        await manager.broadcast(make_stream_state_message(manager.get_state_dict()))

        return {
            "status": "stopped",
            "telemetry": {
                "generated_samples": telem.generated_samples,
                "dropped_samples": telem.dropped_samples,
                "stop_reason": telem.stop_reason,
            },
            "g1_evidence": engine.last_g1_evidence,
            "summary": engine.get_summary(),
        }

    @app.post("/api/device/usb/disconnect")
    async def api_disconnect_usb_device() -> dict[str, Any]:
        engine = manager.device_runtime.canonical_engine
        if engine and engine.is_running:
            try:
                fut = engine.disconnect(timeout_s=2.0)
                await asyncio.wrap_future(fut)
            except Exception:
                pass

        manager.handle_device_disconnect("User requested disconnect via USB API")
        st = manager.device_runtime.get_state_dict()
        await manager.broadcast(make_device_state_message(st))
        return {
            "status": "disconnected",
            "device": st,
        }

    @app.get("/api/device/usb/session")
    def api_get_usb_session() -> dict[str, Any]:
        engine = manager.device_runtime.canonical_engine
        if not engine:
            return {
                "session_state": "DISCONNECTED",
                "is_running": False,
                "port": None,
            }
        return engine.get_summary()

    @app.get("/api/device/usb/g1-evidence")
    def api_get_g1_evidence() -> dict[str, Any]:
        engine = manager.device_runtime.canonical_engine
        if not engine or not engine.last_g1_evidence:
            raise HTTPException(status_code=404, detail="No deterministic G1 evidence report found.")
        return engine.last_g1_evidence

    # ML Research Lab Endpoints
    ml_registry = ResearchModelRegistry()
    ml_service = ResearchInferenceService(registry=ml_registry)

    @app.get("/api/research/ml/models")
    def api_list_research_models() -> list[dict[str, Any]]:
        return [m.to_dict() for m in ml_registry.list_models()]

    @app.get("/api/research/ml/models/{model_id}")
    def api_get_research_model(model_id: str) -> dict[str, Any]:
        m = ml_registry.get_model(model_id)
        if not m:
            raise HTTPException(status_code=404, detail=f"Research model '{model_id}' not found.")
        return m.to_dict()

    @app.post("/api/research/ml/predict")
    async def api_predict_research(req: ResearchPredictRequest) -> dict[str, Any]:
        try:
            return await ml_service.run_patient_murmur_inference(
                file_paths=req.file_paths,
                model_id=req.model_id or "af_murmur_mil_1.0",
                patient_identifier=req.patient_identifier,
                same_subject_attestation=bool(req.same_subject_attestation),
            )
        except SubjectIntegrityError as sie:
            raise HTTPException(status_code=400, detail=str(sie))
        except UnauthorizedPathError as upe:
            raise HTTPException(status_code=400, detail=str(upe))
        except AudioValidationError as ave:
            raise HTTPException(status_code=400, detail=str(ave))
        except ModelUnavailableError as mue:
            raise HTTPException(status_code=503, detail=str(mue))
        except Exception as e:
            # Avoid leaking local drive paths in unexpected exception text
            sanitized = str(e).replace("\\", "/")
            raise HTTPException(status_code=500, detail=f"Research inference failed: {sanitized}")




    # Virtual Integration Bench Endpoints (Software-Only Known-Answer Testing)
    @app.get("/api/bench/scenarios")
    def api_list_bench_scenarios() -> list[dict[str, Any]]:
        runner = VirtualBenchRunner(output_dir="experiments/virtual-bench")
        return runner.list_scenarios()

    @app.post("/api/bench/run")
    def api_run_bench(req: Optional[BenchRunRequest] = None) -> dict[str, Any]:
        scen_id = (req.scenario_id if req else "all") or "all"
        seed = req.seed if req and req.seed is not None else 42
        runner = VirtualBenchRunner(output_dir="experiments/virtual-bench", seed=seed)
        if scen_id == "all":
            report = runner.run_all()
            return report.to_dict()
        else:
            try:
                res = runner.run_scenario(scen_id)
                return res.to_dict()
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))

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

    @app.get("/api/sessions/{session_id}/verify")
    def api_verify_session(session_id: str) -> dict[str, Any]:
        try:
            valid_id = validate_session_id(session_id, manager.sessions_dir)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid session ID")
        return verify_session_integrity(valid_id, manager.sessions_dir)

    @app.get("/api/sessions/{session_id}/manifest")
    def api_get_session_manifest(session_id: str) -> dict[str, Any]:
        try:
            valid_id = validate_session_id(session_id, manager.sessions_dir)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid session ID")
        try:
            return export_session_manifest(valid_id, manager.sessions_dir)
        except FileNotFoundError:
            raise HTTPException(status_code=404, detail="Session not found")

    @app.delete("/api/sessions/{session_id}")
    def api_delete_session(session_id: str) -> dict[str, Any]:
        try:
            valid_id = validate_session_id(session_id, manager.sessions_dir)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid session ID")
        deleted = delete_session(valid_id, manager.sessions_dir)
        if not deleted:
            raise HTTPException(status_code=404, detail="Session not found")
        return {"status": "deleted", "session_id": valid_id}

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
        except (ValueError, FileNotFoundError, SessionCorruptedError) as e:
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
    # Phantom Reference Playback & System Identification Endpoints
    # =========================================================================

    @app.get("/api/scientific/phantom/templates")
    def api_list_phantom_templates() -> list[dict[str, Any]]:
        return analysis.list_phantom_templates()

    @app.post("/api/scientific/phantom/stimulus/generate")
    def api_generate_phantom_stimulus(req: PhantomStimulusGenerateRequest) -> dict[str, Any]:
        try:
            return analysis.generate_phantom_stimulus(
                stimulus_type=req.stimulus_type,
                duration_s=req.duration_s or 5.0,
                sample_rate_hz=req.sample_rate_hz or 48000,
                amplitude_fs=req.amplitude_fs or 0.8,
                save_as_asset=True if req.save_as_asset is None else req.save_as_asset,
                custom_params=req.custom_params,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.post("/api/scientific/phantom/characterize")
    def api_characterize_phantom(req: PhantomCharacterizeRequest) -> dict[str, Any]:
        try:
            return analysis.characterize_phantom(
                asset_id=req.asset_id,
                session_id=req.session_id,
                template_id=req.template_id or "PHANTOM_LOG_SWEEP_20_500HZ_V1",
                trial_id=req.trial_id,
                output_gain_dbfs=req.output_gain_dbfs if req.output_gain_dbfs is not None else -6.0,
                operator_notes=req.operator_notes or "",
                hardware_status=req.hardware_status or "PENDING_PHYSICAL_MEASUREMENT",
                pipeline_buffer_delay_ms=req.pipeline_buffer_delay_ms if req.pipeline_buffer_delay_ms is not None else 30.0,
                max_display_points=req.max_display_points or 300,
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except FileNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @app.get("/api/scientific/phantom/experiments")
    def api_list_phantom_experiments() -> list[dict[str, Any]]:
        return analysis.list_phantom_experiments()

    @app.get("/api/scientific/phantom/experiments/{trial_id}")
    def api_get_phantom_experiment(trial_id: str) -> dict[str, Any]:
        try:
            exp = analysis.get_phantom_experiment(trial_id)
            if not exp:
                raise HTTPException(status_code=404, detail=f"Phantom experiment not found: {trial_id}")
            return exp
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

    # =========================================================================
    # Advisor Metrology Automation Endpoints (Sprint 08)
    # =========================================================================

    @app.get("/api/scientific/metrology/template")
    def api_get_metrology_template() -> dict[str, Any]:
        return analysis.get_metrology_template()

    @app.post("/api/scientific/metrology/run")
    def api_run_metrology_experiment(req: MetrologyRunRequest) -> dict[str, Any]:
        try:
            return analysis.run_metrology_experiment(req.config)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Metrology execution failed: {e}")

    @app.get("/api/scientific/metrology/reports")
    def api_list_metrology_reports() -> list[dict[str, Any]]:
        return analysis.list_metrology_reports()

    @app.get("/api/scientific/metrology/reports/{report_id}")
    def api_get_metrology_report(report_id: str) -> dict[str, Any]:
        try:
            report = analysis.get_metrology_report(report_id)
            if not report:
                raise HTTPException(status_code=404, detail=f"Metrology report not found: {report_id}")
            return report
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.get("/api/scientific/metrology/reports/{report_id}/csv")
    def api_get_metrology_csv(report_id: str) -> Response:
        try:
            csv_data = analysis.get_metrology_summary_csv(report_id)
            if csv_data is None:
                raise HTTPException(status_code=404, detail=f"CSV summary not found for report: {report_id}")
            return Response(content=csv_data, media_type="text/csv")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.get("/api/scientific/metrology/reports/{report_id}/markdown")
    def api_get_metrology_markdown(report_id: str) -> Response:
        try:
            md_data = analysis.get_metrology_summary_markdown(report_id)
            if md_data is None:
                raise HTTPException(status_code=404, detail=f"Markdown report not found for: {report_id}")
            return Response(content=md_data, media_type="text/markdown")
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

    # =========================================================================
    # Engineering Diagnostics & Flight Recorder Endpoints
    # =========================================================================

    @app.get("/api/diagnostics/catalog")
    def api_get_fault_catalog() -> list[dict[str, Any]]:
        return [f.to_dict() for f in list_all_faults()]

    @app.get("/api/diagnostics/events")
    def api_get_diagnostic_events(
        limit: int = 100,
        subsystem: Optional[str] = None,
        severity: Optional[str] = None,
        fault_code: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        fr = get_flight_recorder()
        sub_enum = None
        if subsystem:
            try:
                sub_enum = Subsystem(subsystem.upper())
            except ValueError:
                pass
        sev_enum = None
        if severity:
            try:
                sev_enum = Severity(severity.upper())
            except ValueError:
                pass

        events = fr.get_recent_events(
            limit=limit,
            subsystem=sub_enum,
            severity=sev_enum,
            fault_code=fault_code,
            session_id=session_id,
        )
        return [e.to_dict() for e in events]

    @app.get("/api/diagnostics/active-faults")
    def api_get_active_faults() -> list[dict[str, Any]]:
        fr = get_flight_recorder()
        return [e.to_dict() for e in fr.get_active_faults()]

    @app.get("/api/diagnostics/correlation")
    def api_get_correlation_report() -> dict[str, Any]:
        fr = get_flight_recorder()
        doctor = UsbDiscoveryDoctor(flight_recorder=fr)
        usb_ports = doctor.scan_ports()
        current_port = usb_ports[0].port_name if usb_ports else None
        engine = RootCauseCorrelationEngine(flight_recorder=fr)
        dev_state = manager.device_runtime.get_state_dict()
        is_conn = dev_state.get("state") in ("ready", "streaming")
        report = engine.evaluate_incidents(
            current_port=current_port,
            is_device_connected=is_conn,
            is_streaming=manager.is_streaming,
            is_recording=bool(manager.recorder.is_recording),
        )
        return report.to_dict()

    @app.get("/api/diagnostics/usb/scan")
    def api_scan_usb_ports() -> list[dict[str, Any]]:
        fr = get_flight_recorder()
        doctor = UsbDiscoveryDoctor(flight_recorder=fr)
        descriptors = doctor.scan_ports()
        return [d.to_dict() for d in descriptors]

    @app.post("/api/diagnostics/fault/inject")
    def api_inject_fault(req: FaultInjectRequest) -> dict[str, Any]:
        fr = get_flight_recorder()
        lab = FaultInjectionLab(journal=fr)
        try:
            res = lab.run_scenario(req.scenario_id)
            return {
                "scenario_id": res.scenario_id,
                "name": res.name,
                "target_fault_code": res.target_fault_code,
                "passed": res.passed,
                "diagnostic_message": res.diagnostic_message,
                "emitted_event_id": res.emitted_event_id,
                "severity": res.severity.value,
                "subsystem": res.subsystem.value,
            }
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    @app.post("/api/diagnostics/fault/resolve")
    def api_resolve_fault(req: FaultResolveRequest) -> dict[str, Any]:
        fr = get_flight_recorder()
        resolved_count = fr.resolve_fault(req.fault_code, req.resolution_message)
        return {"fault_code": req.fault_code, "resolved_count": resolved_count}

    @app.post("/api/diagnostics/export")
    def api_export_diagnostics_bundle() -> FileResponse:
        fr = get_flight_recorder()
        doctor = UsbDiscoveryDoctor(flight_recorder=fr)
        ports = doctor.scan_ports()
        exporter = DiagnosticsSupportBundleExporter(flight_recorder=fr)
        export_dir = Path("experiments/diagnostics-bundles")
        export_dir.mkdir(parents=True, exist_ok=True)
        zip_path = exporter.create_bundle(
            output_dir=export_dir,
            device_runtime_state=manager.device_runtime.get_state_dict(),
            device_stats=manager.device_runtime.stats.to_dict(),
            usb_descriptors=[p.to_dict() for p in ports],
        )
        if not zip_path.exists():
            raise HTTPException(status_code=500, detail="Failed to create diagnostics bundle")
        return FileResponse(
            path=str(zip_path),
            filename=zip_path.name,
            media_type="application/zip",
        )

    # WebSocket Real-Time Ingestion & Command Endpoint
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket) -> None:
        origin = websocket.headers.get("origin")
        # Validate WebSocket Origin if present (allows test clients/headless tools while guarding browsers)
        if origin and origin not in origins:
            await websocket.close(code=1008)  # 1008: Policy Violation
            return

        if auth_token:
            token = websocket.query_params.get("token") or websocket.headers.get("x-auscultaforge-auth")
            if token != auth_token:
                await websocket.close(code=1008, reason="Unauthorized")
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

                elif action == "poll_device":
                    candidates = manager.device_runtime.discovery_provider.poll_candidates()
                    manager.device_runtime.event_log.log(
                        "DEVICE_SCAN_EXECUTED",
                        f"Hardware discovery scan executed ({len(candidates)} candidate devices detected)",
                        severity="info",
                        metadata={"candidate_count": len(candidates)},
                    )
                    st = manager.device_runtime.get_state_dict()
                    await websocket.send_json(make_device_state_message(st))
                    await manager.broadcast(make_device_state_message(st))

                elif action == "disconnect_device":
                    if manager.device_runtime.state in (DeviceState.READY, DeviceState.STREAMING):
                        manager.handle_device_disconnect("User requested device disconnect via WebSocket")
                        await manager.broadcast(make_device_state_message(manager.device_runtime.get_state_dict()))
                    else:
                        await websocket.send_json(make_device_state_message(manager.device_runtime.get_state_dict()))

                elif action == "ping":
                    await websocket.send_json({"type": "pong", "time": time.time()})

        except WebSocketDisconnect:
            pass
        finally:
            manager.unregister_client(websocket)

    return app
