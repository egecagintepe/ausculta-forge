"""AuscultaForge Desktop — Standalone Python Backend Bundler.

Uses PyInstaller to bundle the complete Python runtime, FastAPI application,
Uvicorn ASGI server, and scientific PCG core (NumPy, SciPy, PyWavelets)
into an auditable, self-contained one-directory distribution.
"""

import os
from pathlib import Path
import shutil
import subprocess
import sys

HIDDEN_IMPORTS = [
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "fastapi",
    "fastapi.middleware.cors",
    "starlette",
    "starlette.middleware",
    "starlette.middleware.base",
    "starlette.responses",
    "starlette.websockets",
    "pydantic",
    "scipy.signal",
    "scipy.io.wavfile",
    "pywt",
    "numpy",
]


def build_backend(output_dir: Path | str = None) -> Path:
    software_dir = Path(__file__).parent.resolve()
    repo_root = software_dir.parent
    entrypoint = software_dir / "pcg_app" / "desktop_server.py"

    target_dir = Path(output_dir).resolve() if output_dir else software_dir / "dist_backend"
    work_dir = software_dir / "build_backend"

    print(f"[BUILD] Bundling AuscultaForge backend from {entrypoint}...")
    print(f"[BUILD] Target output directory: {target_dir}")

    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onedir",
        "--name",
        "auscultaforge-backend",
        "--distpath",
        str(target_dir),
        "--workpath",
        str(work_dir),
        "--paths",
        str(software_dir),
    ]

    for imp in HIDDEN_IMPORTS:
        cmd.extend(["--hidden-import", imp])

    cmd.append(str(entrypoint))

    result = subprocess.run(cmd, cwd=str(software_dir))
    if result.returncode != 0:
        raise RuntimeError(f"PyInstaller build failed with return code {result.returncode}")

    binary_dir = target_dir / "auscultaforge-backend"
    exe_name = "auscultaforge-backend.exe" if sys.platform == "win32" else "auscultaforge-backend"
    exe_path = binary_dir / exe_name

    if not exe_path.exists():
        raise FileNotFoundError(f"Expected bundled backend executable not found at {exe_path}")

    print(f"[BUILD] Backend bundling SUCCESSFUL: {exe_path}")
    return binary_dir


if __name__ == "__main__":
    build_backend()
