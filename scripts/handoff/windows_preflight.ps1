param(
    [switch]$Json,
    [string]$Output = ""
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent

# Refresh User PATH in current process so newly installed WinGet tools (Python 3.11, WinLibs GCC, Node) are visible
$machinePath = [System.Environment]::GetEnvironmentVariable('Path', 'Machine')
$userPath = [System.Environment]::GetEnvironmentVariable('Path', 'User')
if ($machinePath -or $userPath) {
    $env:Path = "$machinePath;$userPath;$env:Path"
}

$venvPython = Join-Path $repoRoot '.venv\Scripts\python.exe'
$systemPy = $null
if (Test-Path -LiteralPath $venvPython) {
    $pyExe = $venvPython
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $pyExe = "py"
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $pyExe = "python"
} else {
    throw "Neither .venv\Scripts\python.exe nor system Python was found. Run scripts\handoff\windows_setup.ps1 first."
}

$pyCode = @'
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

repo = Path(sys.argv[1]).absolute()
soft = repo / "software"
if str(soft) not in sys.path:
    sys.path.insert(0, str(soft))

path_str = str(repo)
ascii_safe = bool(re.fullmatch(r"[\x20-\x7E]+", path_str)) and (" " not in path_str)

def run_short(cmd):
    try:
        res = subprocess.run(cmd, cwd=repo, capture_output=True, text=True, timeout=10, encoding="utf-8", errors="replace")
        return res.returncode, res.stdout.strip(), res.stderr.strip()
    except Exception as exc:
        return 1, "", str(exc)

git_rc, head_sha, _ = run_short(["git", "rev-parse", "HEAD"])
if git_rc == 0 and (repo / ".git").exists():
    checkout_mode = "GIT_CLONE"
    _, branch_name, _ = run_short(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    _, git_dirty, _ = run_short(["git", "status", "--short"])
else:
    checkout_mode = "GITHUB_DOWNLOAD_ZIP"
    branch_name = "NONE (ZIP)"
    git_dirty = False
    head_sha = None
    try:
        from pcg_app import hardware_workflow as hw
        head_sha = hw.git_info(repo).get("commit")
    except Exception:
        pass

modules_required = ("numpy", "scipy", "fastapi", "uvicorn", "serial", "pywt", "esptool", "pytest")
modules = {name: (importlib.util.find_spec(name) is not None) for name in modules_required}

node_path = shutil.which("node")
npm_path = shutil.which("npm.cmd") or shutil.which("npm")
node_ver = None
node_compatible = False
if node_path:
    rc, out, _ = run_short([node_path, "--version"])
    if rc == 0:
        node_ver = out
        m = re.match(r"v?(\d+)\.(\d+)\.(\d+)", out)
        if m:
            maj, mino, _ = int(m.group(1)), int(m.group(2)), int(m.group(3))
            node_compatible = (maj == 20 and mino >= 19) or (maj >= 22)

gcc_path = shutil.which("gcc")
idf_py = shutil.which("idf.py")
idf_installed_at_default = Path(r"C:\esp\esp-idf-v5.5.1\export.ps1").is_file()

ports = []
try:
    from pcg_app.diagnostics.usb_doctor import UsbDiscoveryDoctor
    ports = [p.to_dict() for p in UsbDiscoveryDoctor().scan_ports()]
except Exception:
    ports = []

def check_manifest(rel_path, expected_candidate=False):
    m_path = repo / rel_path
    if not m_path.is_file():
        return {"present": False, "status": "MISSING", "path": rel_path}
    try:
        data = json.loads(m_path.read_text(encoding="utf-8"))
        status = data.get("status", "UNKNOWN")
        from pcg_app import hardware_workflow as hw
        if expected_candidate and status == "PREPARED_NOT_AUTHORIZED_FOR_FLASH":
            base, _ = hw._resolve_and_verify_manifest_artifacts(m_path.resolve(), data)
            return {"present": True, "hashes_verified": True, "status": status, "build_directory": str(base), "source_modes": data.get("source_modes")}
        validated = hw.validate_release(m_path)
        return {"present": True, "hashes_verified": True, "status": validated.get("status"), "build_directory": validated.get("build_directory"), "source_modes": validated.get("source_modes")}
    except Exception as exc:
        return {"present": True, "hashes_verified": False, "status": "INVALID", "error": str(exc)}

manifests = {
    "g1_rollback_backup": check_manifest("firmware/g1_rollback_backup/firmware_build_manifest.json"),
    "g1_staged_release": check_manifest("firmware/releases/g1_release_20261117/firmware_build_manifest.json"),
    "g2_staged_candidate": check_manifest("firmware/releases/g2_candidate_20261117/firmware_build_manifest.json", expected_candidate=True),
}

report = {
    "repo_root": path_str,
    "path_ascii_no_spaces": ascii_safe,
    "recommended_ascii_junction": r"C:\pcg_starter" if not ascii_safe else None,
    "git": {"checkout_mode": checkout_mode, "branch": branch_name, "head": head_sha or "UNKNOWN", "dirty": bool(git_dirty)},
    "python": {
        "executable": sys.executable,
        "version": sys.version.split()[0],
        "in_project_venv": (Path(sys.prefix).absolute() == (repo / ".venv").absolute()),
        "modules": modules,
        "all_modules_ready": all(modules.values()),
    },
    "frontend": {
        "node": node_ver,
        "node_compatible": node_compatible,
        "npm_available": bool(npm_path),
        "node_modules_present": (repo / "software/frontend/node_modules").is_dir(),
    },
    "toolchains": {
        "host_gcc": gcc_path or "MISSING",
        "esp_idf_in_shell": idf_py or "NOT_ACTIVE",
        "esp_idf_5_5_1_present": idf_installed_at_default,
    },
    "manifests": manifests,
    "passive_com_ports": ports,
    "espressif_candidates": [p["port_name"] for p in ports if p.get("is_espressif_candidate")],
    "PHYSICAL_PORT_POLICY": "Passive scan only; single owner per COM port; never hardcode COM10.",
}
print(json.dumps(report, indent=2, ensure_ascii=False))
'@

$tempPy = [System.IO.Path]::GetTempFileName() + ".py"
try {
    [System.IO.File]::WriteAllText($tempPy, $pyCode, [System.Text.UTF8Encoding]::new($false))
    if ($pyExe -eq "py") {
        $jsonOut = & py -3.11 $tempPy $repoRoot
    } else {
        $jsonOut = & $pyExe $tempPy $repoRoot
    }
    if ($LASTEXITCODE -ne 0) {
        throw "Preflight inspection script failed with exit code $LASTEXITCODE."
    }
} finally {
    Remove-Item -LiteralPath $tempPy -ErrorAction SilentlyContinue
}

if ($Output) {
    $outDir = Split-Path -Parent $Output
    if ($outDir -and -not (Test-Path -LiteralPath $outDir)) {
        New-Item -ItemType Directory -Path $outDir -Force | Out-Null
    }
    [System.IO.File]::WriteAllText($Output, ($jsonOut -join "`n") + "`n", [System.Text.UTF8Encoding]::new($false))
}

if ($Json) {
    $jsonOut
    exit 0
}

$parsed = $jsonOut | ConvertFrom-Json
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  AuscultaForge — Windows Handoff Preflight (Passive)" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ("Repo Root    : {0}" -f $parsed.repo_root)
if (-not $parsed.path_ascii_no_spaces) {
    Write-Host ("Path Warning : Contains spaces/non-ASCII chars. Use junction {0} for ESP-IDF builds." -f $parsed.recommended_ascii_junction) -ForegroundColor Yellow
}
Write-Host ("Mode / HEAD  : {0} | {1} (branch: {2}, dirty: {3})" -f $parsed.git.checkout_mode, $parsed.git.head, $parsed.git.branch, $parsed.git.dirty)
Write-Host ("Python       : {0} (venv={1}, modules_ok={2})" -f $parsed.python.version, $parsed.python.in_project_venv, $parsed.python.all_modules_ready)
Write-Host ("Frontend     : Node={0} (ok={1}), node_modules={2}" -f $parsed.frontend.node, $parsed.frontend.node_compatible, $parsed.frontend.node_modules_present)
Write-Host ("GCC / IDF    : gcc={0} | idf_shell={1}" -f $parsed.toolchains.host_gcc, $parsed.toolchains.esp_idf_in_shell)
Write-Host "Manifests    :"
Write-Host ("  - G1 Rollback Backup : hashes_ok={0} | status={1}" -f $parsed.manifests.g1_rollback_backup.hashes_verified, $parsed.manifests.g1_rollback_backup.status)
Write-Host ("  - G1 Staged Release  : present={0} | hashes_ok={1} | status={2}" -f $parsed.manifests.g1_staged_release.present, $parsed.manifests.g1_staged_release.hashes_verified, $parsed.manifests.g1_staged_release.status)
Write-Host ("  - G2 Staged Candidate: present={0} | hashes_ok={1} | status={2}" -f $parsed.manifests.g2_staged_candidate.present, $parsed.manifests.g2_staged_candidate.hashes_verified, $parsed.manifests.g2_staged_candidate.status)
$candText = if ($parsed.espressif_candidates.Count -gt 0) { $parsed.espressif_candidates -join ", " } else { "NONE_DETECTED" }
Write-Host ("ESP32 Ports  : {0}" -f $candText)
Write-Host "==========================================================" -ForegroundColor Cyan
