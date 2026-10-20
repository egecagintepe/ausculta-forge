"""End-to-End Subprocess Test for AuscultaForge Desktop Dedicated Server."""

import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request
import urllib.error
import pytest


def test_desktop_server_subprocess_lifecycle(tmp_path: Path):
    """Test desktop_server startup, handshake emission, auth protection, and clean shutdown."""
    handshake_file = tmp_path / "handshake.json"
    user_data_dir = tmp_path / "user_data"

    python_exe = sys.executable
    cmd = [
        python_exe,
        "-m",
        "pcg_app.desktop_server",
        "--port",
        "0",
        "--user-data-dir",
        str(user_data_dir),
        "--handshake-file",
        str(handshake_file),
        "--parent-pid",
        str(os.getpid()),
    ]

    # Launch server subprocess
    proc = subprocess.Popen(
        cmd,
        cwd=str(Path(__file__).parent.parent),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    handshake_data = None
    start_time = time.time()
    try:
        # Read stdout until ready signal
        for line in proc.stdout:
            if "AUSCULTAFORGE_BACKEND_READY:" in line:
                raw_json = line.split("AUSCULTAFORGE_BACKEND_READY:", 1)[1].strip()
                handshake_data = json.loads(raw_json)
                break
            if time.time() - start_time > 10.0:
                break

        assert handshake_data is not None, "Desktop server failed to emit ready handshake"
        port = handshake_data["port"]
        auth_token = handshake_data["auth_token"]
        assert port > 0
        assert len(auth_token) == 64  # 32 bytes hex

        # Check handshake file was created
        assert handshake_file.exists()
        file_data = json.loads(handshake_file.read_text(encoding="utf-8"))
        assert file_data["port"] == port

        # Check subdirectories were created
        assert (user_data_dir / "sessions").is_dir()
        assert (user_data_dir / "reports").is_dir()
        assert (user_data_dir / "logs").is_dir()

        base_url = f"http://127.0.0.1:{port}"

        # 1. Health check (unauthenticated permitted)
        with urllib.request.urlopen(f"{base_url}/api/health") as response:
            assert response.status == 200
            res = json.loads(response.read().decode("utf-8"))
            assert res["status"] == "ok"
            assert res["app"] == "AuscultaForge"

        # 2. Status without auth header should fail with 403
        req_unauth = urllib.request.Request(f"{base_url}/api/status")
        with pytest.raises(urllib.error.HTTPError) as excinfo:
            urllib.request.urlopen(req_unauth)
        assert excinfo.value.code == 403

        # 3. Status with auth header should succeed
        req_auth = urllib.request.Request(
            f"{base_url}/api/status",
            headers={"X-AuscultaForge-Auth": auth_token},
        )
        with urllib.request.urlopen(req_auth) as response:
            assert response.status == 200
            res = json.loads(response.read().decode("utf-8"))
            assert "capabilities" in res

    finally:
        # Graceful shutdown
        proc.terminate()
        try:
            proc.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
