# ADR-0013: Bridge Architecture — FastAPI Factory Pattern & WebSockets
**Status:** `ACCEPTED`  
**Date:** 2026-09-26 (Hardened in Sprint 01 & Master Integration)  
**Deciders:** Module C (Ege)  
**Technical Area:** Web Services & Interprocess Communication

## Context & Problem Statement
To connect the local desktop browser user interface (React / Vite) with the Python DSP and device runtime backend, a local communications bridge is required. The team evaluated architecture patterns for local service exposure.

## Decision Drivers
* Real-time streaming capability: Pushing high-frequency audio vectors ($\le 600$ points) at 30–60 Hz to the browser with minimal latency.
* Structured REST API: Exposing device status, control endpoints, and metrology reports.
* Clean testing isolation: Preventing global state leaks between unit test cases.

## Considered Alternatives
1. **Flask + Flask-SocketIO:** Mature, but synchronous WSGI architecture struggles with high-throughput asynchronous WebSockets without heavy monkey-patching (`gevent`/`eventlet`).
2. **Electron IPC (Desktop Monolith):** Bundles Chromium and Node.js into a massive binary ($> 200\text{ MB}$), complicating cross-platform build pipelines and Python integration.
3. **FastAPI (ASGI) with Application Factory Pattern:** Built on Starlette and Pydantic; native asynchronous coroutines (`asyncio`); built-in WebSocket support; automatic OpenAPI documentation.

## Decision
Selected **FastAPI with the Application Factory Pattern (`create_app()` in `software/pcg_app/app.py`)**:
* **Factory Pattern:** Eliminates a global module-level `app` object; allows tests to instantiate isolated app instances with temporary test session directories.
* **WebSocket Streaming:** Pushes decimated audio vectors and live telemetry over `ws://127.0.0.1:8000/ws`.
* **REST Endpoints:** Exposes 57 strongly-typed endpoints for session management, metrology reports, and research benchmarks.

## Consequences & Trade-Offs
* **Positive:** High performance; asynchronous non-blocking event loop; automatic Swagger docs at `/docs`.
* **Negative:** Uvicorn CLI commands must use the `--factory` flag (`uvicorn pcg_app.app:create_app --factory`).
