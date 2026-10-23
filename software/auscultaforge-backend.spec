# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
software_dir = Path(SPECPATH).resolve()
a = Analysis(
    [str(software_dir / 'pcg_app' / 'desktop_server.py')],
    pathex=[str(software_dir)],
    binaries=[],
    datas=[],
    hiddenimports=['uvicorn.logging', 'uvicorn.loops', 'uvicorn.loops.auto', 'uvicorn.protocols', 'uvicorn.protocols.http', 'uvicorn.protocols.http.auto', 'uvicorn.protocols.websockets', 'uvicorn.protocols.websockets.auto', 'uvicorn.lifespan', 'uvicorn.lifespan.on', 'fastapi', 'fastapi.middleware.cors', 'starlette', 'starlette.middleware', 'starlette.middleware.base', 'starlette.responses', 'starlette.websockets', 'pydantic', 'scipy.signal', 'scipy.io.wavfile', 'pywt', 'numpy', 'serial', 'serial.tools.list_ports', 'serial.tools.list_ports_windows'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='auscultaforge-backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='auscultaforge-backend',
)
