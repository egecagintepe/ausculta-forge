"""AuscultaForge Desktop — Dedicated Production Backend Server Runner.

Handles:
1. Dynamic ephemeral port allocation (eliminates port 8000 collisions).
2. Cryptographic per-instance authentication token generation.
3. Windows User-Data directory resolution (%APPDATA%\\AuscultaForge).
4. Machine-readable startup handshake reporting (stdout & file).
5. Parent process watchdog monitoring (automatic termination if parent exits).
"""

import argparse
import ctypes
import json
import logging
import os
from pathlib import Path
import secrets
import sys
import threading
import time
from typing import Optional

import uvicorn

try:
    from .app import create_app
except ImportError:
    from pcg_app.app import create_app

logger = logging.getLogger("auscultaforge.desktop_server")


def get_default_user_data_dir() -> Path:
    """Resolve the platform-appropriate user data storage directory."""
    if sys.platform == "win32":
        app_data = os.environ.get("APPDATA")
        if app_data:
            return Path(app_data) / "AuscultaForge"
    return Path.home() / ".auscultaforge"


def is_pid_alive(pid: int) -> bool:
    """Check whether a process ID is currently running on the operating system."""
    if pid <= 0:
        return True
    if sys.platform == "win32":
        STILL_ACTIVE = 259
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            return False
        exit_code = ctypes.c_ulong()
        ctypes.windll.kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code))
        ctypes.windll.kernel32.CloseHandle(handle)
        return exit_code.value == STILL_ACTIVE
    else:
        try:
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False


def start_parent_watchdog(parent_pid: int, server: uvicorn.Server) -> None:
    """Spawn a background daemon thread that triggers server exit if parent terminates."""
    def _watchdog_loop():
        while not server.should_exit:
            if not is_pid_alive(parent_pid):
                logger.info(f"Parent process (PID {parent_pid}) terminated; initiating clean shutdown.")
                server.should_exit = True
                break
            time.sleep(1.0)

    t = threading.Thread(target=_watchdog_loop, daemon=True, name="ParentProcessWatchdog")
    t.start()


def build_handshake_payload(
    host: str,
    port: int,
    auth_token: Optional[str],
    user_data_dir: str | Path,
    pid: int,
) -> dict:
    """Build the standardized, versioned handshake dictionary."""
    base_data_dir = Path(user_data_dir).resolve()
    sessions_dir = base_data_dir / "sessions"
    assets_dir = base_data_dir / "assets"
    analysis_dir = base_data_dir / "analysis"
    reports_dir = base_data_dir / "reports"
    logs_dir = base_data_dir / "logs"
    return {
        "schema_version": "1.0.0",
        "app": "AuscultaForge Desktop",
        "version": "0.1.0-alpha.1",
        "status": "ready",
        "host": host,
        "port": port,
        "auth_token": auth_token,
        "pid": pid,
        "storage_dir": str(base_data_dir),
        "user_data_dir": str(base_data_dir),
        "sessions_dir": str(sessions_dir),
        "assets_dir": str(assets_dir),
        "analysis_dir": str(analysis_dir),
        "reports_dir": str(reports_dir),
        "logs_dir": str(logs_dir),
        "health_url": f"http://{host}:{port}/api/health",
    }


def run_desktop_server(
    host: str = "127.0.0.1",
    port: int = 0,
    auth_token: Optional[str] = "auto",
    user_data_dir: Optional[str | Path] = None,
    handshake_file: Optional[str | Path] = None,
    parent_pid: Optional[int] = None,
) -> None:
    """Run the AuscultaForge desktop backend server."""
    # 1. Resolve User Data Directories
    base_data_dir = Path(user_data_dir).resolve() if user_data_dir else get_default_user_data_dir()
    sessions_dir = base_data_dir / "sessions"
    assets_dir = base_data_dir / "assets"
    analysis_dir = base_data_dir / "analysis"
    reports_dir = base_data_dir / "reports"
    logs_dir = base_data_dir / "logs"
    cache_dir = base_data_dir / "cache"

    for d in (sessions_dir, assets_dir, analysis_dir, reports_dir, logs_dir, cache_dir):
        d.mkdir(parents=True, exist_ok=True)

    # Configure file logging in logs_dir
    log_file = logs_dir / "backend.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s",
        handlers=[
            logging.FileHandler(str(log_file), encoding="utf-8"),
            logging.StreamHandler(sys.stderr),
        ],
    )
    logger.info(f"AuscultaForge Desktop Server starting. User data: {base_data_dir}")

    # 2. Resolve Authentication Token
    if auth_token == "auto" or auth_token is None:
        resolved_token = secrets.token_hex(32)
    elif auth_token == "disabled":
        resolved_token = None
    else:
        resolved_token = str(auth_token)

    # 3. Create Application with isolated user directories
    app = create_app(
        sessions_dir=sessions_dir,
        assets_dir=assets_dir,
        analysis_dir=analysis_dir,
        auth_token=resolved_token,
    )

    # 4. Bind Socket with Dynamic Ephemeral Port Allocation
    config = uvicorn.Config(
        app=app,
        host=host,
        port=port,
        log_level="info",
        access_log=False,
    )
    sock = config.bind_socket()
    actual_port = sock.getsockname()[1]
    logger.info(f"Socket successfully bound to {host}:{actual_port}")

    # 5. Emit Machine-Readable Handshake Record
    handshake_payload = build_handshake_payload(
        host=host,
        port=actual_port,
        auth_token=resolved_token,
        user_data_dir=base_data_dir,
        pid=os.getpid(),
    )

    handshake_json = json.dumps(handshake_payload)

    if handshake_file:
        h_path = Path(handshake_file).resolve()
        h_path.parent.mkdir(parents=True, exist_ok=True)
        h_path.write_text(handshake_json, encoding="utf-8")
        logger.info(f"Handshake JSON written to: {h_path}")

    # Output token line to stdout for parent process parsing
    print(f"AUSCULTAFORGE_BACKEND_READY:{handshake_json}", flush=True)

    # 6. Initialize Server & Watchdog
    server = uvicorn.Server(config)
    if parent_pid and parent_pid > 0:
        logger.info(f"Registering parent process watchdog for PID {parent_pid}")
        start_parent_watchdog(parent_pid, server)

    # 7. Serve Requests
    try:
        server.run(sockets=[sock])
    finally:
        logger.info("AuscultaForge Desktop Server stopped cleanly.")
        if handshake_file and Path(handshake_file).exists():
            try:
                Path(handshake_file).unlink()
            except OSError:
                pass


def main() -> None:
    parser = argparse.ArgumentParser(description="AuscultaForge Desktop Dedicated Server")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host interface (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=0, help="Port to bind (default: 0 for dynamic ephemeral port)")
    parser.add_argument("--auth-token", type=str, default="auto", help="Auth token ('auto', 'disabled', or secret)")
    parser.add_argument("--user-data-dir", type=str, default=None, help="Root path for persistent user data")
    parser.add_argument("--handshake-file", type=str, default=None, help="Path to write readiness handshake JSON")
    parser.add_argument("--parent-pid", type=int, default=None, help="Parent process ID to monitor")
    parser.add_argument(
        "--print-handshake",
        action="store_true",
        help="Print handshake payload and exit without starting uvicorn",
    )
    args = parser.parse_args()

    if args.print_handshake:
        base_dir = Path(args.user_data_dir).resolve() if args.user_data_dir else get_default_user_data_dir()
        token = (
            secrets.token_hex(32)
            if (args.auth_token == "auto" or not args.auth_token)
            else (None if args.auth_token == "disabled" else args.auth_token)
        )
        payload = build_handshake_payload(
            host=args.host,
            port=args.port if args.port > 0 else 58903,
            auth_token=token,
            user_data_dir=base_dir,
            pid=os.getpid(),
        )
        print(f"AUSCULTAFORGE_BACKEND_READY:{json.dumps(payload)}", flush=True)
        return

    run_desktop_server(
        host=args.host,
        port=args.port,
        auth_token=args.auth_token,
        user_data_dir=args.user_data_dir,
        handshake_file=args.handshake_file,
        parent_pid=args.parent_pid,
    )


if __name__ == "__main__":
    main()
