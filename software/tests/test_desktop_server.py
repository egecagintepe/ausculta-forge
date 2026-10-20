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
        assert handshake_data["schema_version"] == "1.0.0"
        assert handshake_data["status"] == "ready"
        assert handshake_data["storage_dir"] == str(user_data_dir.resolve())
        assert handshake_data["user_data_dir"] == str(user_data_dir.resolve())

        # Check handshake file was created
        assert handshake_file.exists()
        file_data = json.loads(handshake_file.read_text(encoding="utf-8"))
        assert file_data["port"] == port
        assert file_data["storage_dir"] == str(user_data_dir.resolve())

        # Check subdirectories were created
        assert (user_data_dir / "sessions").is_dir()
        assert (user_data_dir / "assets").is_dir()
        assert (user_data_dir / "analysis").is_dir()
        assert (user_data_dir / "reports").is_dir()
        assert (user_data_dir / "logs").is_dir()

        base_url = f"http://127.0.0.1:{port}"

        # 1. Health check (unauthenticated permitted)
        with urllib.request.urlopen(f"{base_url}/api/health") as response:
            assert response.status == 200
            res = json.loads(response.read().decode("utf-8"))
            assert res["status"] in ("healthy", "ok")
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


def test_desktop_server_unicode_and_spaces_path(tmp_path: Path):
    """Test desktop_server with user data directory containing spaces and Unicode characters."""
    unicode_user_data = tmp_path / "AuscultaForge Veri Alanı 🩺"
    handshake_file = unicode_user_data / "handshake.json"

    python_exe = sys.executable
    cmd = [
        python_exe,
        "-m",
        "pcg_app.desktop_server",
        "--port",
        "0",
        "--user-data-dir",
        str(unicode_user_data),
        "--handshake-file",
        str(handshake_file),
        "--parent-pid",
        str(os.getpid()),
    ]

    proc = subprocess.Popen(
        cmd,
        cwd=str(Path(__file__).parent.parent),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    try:
        handshake_data = None
        start_time = time.time()
        for line in proc.stdout:
            if "AUSCULTAFORGE_BACKEND_READY:" in line:
                raw_json = line.split("AUSCULTAFORGE_BACKEND_READY:", 1)[1].strip()
                handshake_data = json.loads(raw_json)
                break
            if time.time() - start_time > 10.0:
                break

        assert handshake_data is not None, "Failed to start server with Unicode path"
        assert handshake_data["storage_dir"] == str(unicode_user_data.resolve())
        assert (unicode_user_data / "sessions").is_dir()
        assert (unicode_user_data / "logs").is_dir()

        # Verify health check succeeds
        base_url = f"http://127.0.0.1:{handshake_data['port']}"
        with urllib.request.urlopen(f"{base_url}/api/health") as response:
            assert response.status == 200
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
