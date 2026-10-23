"""First-contact workflows. No probing or flashing during passive discovery."""
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid

from .canonical.engine import CanonicalSessionEngine
from .canonical.acceptance import assess_g1
from .canonical.transport import UsbCdcAcmAdapter
from .diagnostics.flight_recorder import get_flight_recorder
from .diagnostics.usb_doctor import UsbDiscoveryDoctor

ROOT = Path(__file__).resolve().parents[2]
PINNED_IDF = "5.5.1"


def sdk_python():
    environment = os.environ.get("IDF_PYTHON_ENV_PATH")
    if environment:
        candidate = Path(environment)/("Scripts/python.exe" if os.name=="nt" else "bin/python")
        if candidate.exists():
            return str(candidate)
    return sys.executable


def idf_command(idf, *arguments):
    # On Windows idf.py may resolve to Espressif's PE launcher, not a Python script.
    return ([idf] if str(idf).lower().endswith(".exe") else [sdk_python(),idf]) + list(arguments)


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def sha256(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")


def run(command, **kwargs):
    return subprocess.run(command, capture_output=True, text=True, timeout=30,
                          encoding="utf-8", errors="replace", **kwargs)


def git_info(root=ROOT):
    if not shutil.which("git"):
        return {"commit":None,"state":"GIT_UNAVAILABLE"}
    try:
        commit = run(["git","rev-parse","HEAD"],cwd=root)
        return {"commit":commit.stdout.strip() if not commit.returncode else None,
                "state":run(["git","status","--short","--branch"],cwd=root).stdout.strip()
                    if not commit.returncode else "NOT_A_GIT_CHECKOUT"}
    except (OSError,subprocess.SubprocessError):
        return {"commit":None,"state":"UNAVAILABLE"}


def preflight(root=ROOT):
    """Passive: port enumeration only; no serial open, DTR toggle or packet write."""
    tools = {name: shutil.which(name) for name in ("git","idf.py","xtensa-esp-elf-gcc","cmake","ninja")}
    idf = tools["idf.py"]
    version = run(idf_command(idf,"--version")).stdout.strip() if idf else None
    modules = {name: importlib.util.find_spec(name) is not None
               for name in ("serial","fastapi","uvicorn","numpy","scipy")}
    backend_ready = False
    backend_detail = "Required packages missing"
    if all(modules.values()):
        try:
            check = run([sys.executable,"-c",
                "import sys; sys.path.insert(0,sys.argv[1]); from pcg_app.app import create_app; print('READY')",
                str(root/"software")],cwd=root)
            backend_ready = check.returncode == 0
            backend_detail = "Backend import verified; HTTP listener not started" if backend_ready else check.stderr[-2000:]
        except (OSError,subprocess.SubprocessError) as exc:
            backend_detail = str(exc)
    required = ["firmware/CMakeLists.txt","firmware/main/idf_component.yml",
                "firmware/dependencies.lock","firmware/sdkconfig.defaults",
                "software/pcg_app/canonical/engine.py","software/pcg_app/app.py"]
    files = {p:(root/p).is_file() for p in required}
    ports = [p.to_dict() for p in UsbDiscoveryDoctor().scan_ports()]
    cache = root/"firmware/build/release/CMakeCache.txt"
    cache_status = "ABSENT"
    if cache.exists():
        text = cache.read_text(encoding="utf-8",errors="replace")
        cache_status = "COMPATIBLE" if "IDF_TARGET:STRING=esp32s3" in text else "REVIEW_REQUIRED"
    ready = all(tools.values()) and version is not None and PINNED_IDF in version and all(files.values())
    return {"created_utc":utc_now(), "git":git_info(root), "python":sys.executable,
            "python_version":sys.version,"tools":tools,"idf_version":version,"modules":modules,"source_files":files,
            "build_cache":cache_status,"ports":ports,
            "BOARD_ATTACHED":"CANDIDATE_NOT_VERIFIED" if any(p["is_espressif_candidate"] for p in ports) else "NOT_DETECTED",
            "ESP_IDF":"READY" if idf and version and PINNED_IDF in version else "NOT_READY",
            "FIRMWARE_BUILD":"READY" if ready else "NOT_READY",
            "USB_CDC_HOST":"READY" if modules["serial"] else "NOT_READY",
            "DESKTOP_BACKEND":"READY" if backend_ready else "NOT_READY",
            "backend_check":backend_detail,
            "HARDWARE_TEST":"NOT_EXECUTED", "cable_data_capability":"USER_CHECK_REQUIRED",
            "port_access":"NOT_PROBED (opening a port may reset hardware)",
            "next_action":"Use pinned ESP-IDF exported shell; inspect connector/cable and select a known board. Close only the monitor owning its COM port."}


def build_release(root=ROOT):
    """Only a genuine zero-exit idf build can create a flashable manifest."""
    idf = shutil.which("idf.py")
    if not idf:
        raise RuntimeError("ESP-IDF unavailable. Open the pinned 5.5.1 exported shell; no flashing permitted.")
    result = run(idf_command(idf,"--version"))
    if result.returncode or PINNED_IDF not in result.stdout:
        raise RuntimeError(f"Expected ESP-IDF {PINNED_IDF}: {result.stdout}{result.stderr}")
    firmware = root/"firmware"
    build = firmware/"build/release"
    build.mkdir(parents=True,exist_ok=True)
    cache = build/"CMakeCache.txt"
    actions = ["reconfigure","build"] if cache.exists() else ["set-target","esp32s3","build"]
    command = idf_command(idf,"-B",str(build),*actions)
    log_path = firmware/"build/release-build-output.txt"
    with log_path.open("w",encoding="utf-8") as log:
        completed = subprocess.run(command,cwd=firmware,stdout=log,stderr=subprocess.STDOUT,timeout=1200)
    if completed.returncode:
        raise RuntimeError(f"ESP-IDF build failed ({completed.returncode}); see {log_path}. STOP BEFORE FLASH.")
    config = (firmware/"sdkconfig").read_text(encoding="utf-8")
    for expected in ('CONFIG_IDF_TARGET="esp32s3"',"CONFIG_ESPTOOLPY_FLASHSIZE_16MB=y",
                     "CONFIG_SPIRAM_MODE_OCT=y","CONFIG_SPIRAM_SPEED_80M=y"):
        if expected not in config:
            raise RuntimeError(f"Build configuration mismatch: {expected}")
    flash = json.loads((build/"flasher_args.json").read_text())
    description = json.loads((build/"project_description.json").read_text())
    hashes = {path:sha256(build/path) for path in flash["flash_files"].values()}
    compiler = shutil.which("xtensa-esp-elf-gcc")
    manifest = {"status":"COMPILED_BUT_NOT_FLASHED","created_utc":utc_now(),**git_info(root),
        "firmware_version":description["project_version"],"idf_version":PINNED_IDF,"esp_tinyusb":"2.2.0","tinyusb":"0.19.0~3",
        "target":"esp32s3","flash_mb":16,"psram_mb":8,"profile":2,"encoding":1,
        "memory_origin":"CONFIGURED_TARGET_NOT_PHYSICALLY_VERIFIED",
        "source_modes":[1,0] if "CONFIG_AF_I2S_CONFIRMED_PROFILE=y" in config else [1],
        "microphone_required_for_boot":False,"physical_boot":"NOT_EXECUTED",
        "compiler":run([compiler,"--version"]).stdout if compiler else None,
        "build_directory":str(build),"binary_sha256":hashes,
        "sdkconfig_sha256":sha256(firmware/"sdkconfig"),
        "dependencies_lock_sha256":sha256(firmware/"dependencies.lock"),
        "partition_layout":(firmware/"partitions.csv").read_text(),"flash_files":flash["flash_files"]}
    write_json(build/"firmware_build_manifest.json",manifest)
    return manifest


def validate_release(manifest_path):
    manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    if manifest.get("status") != "COMPILED_BUT_NOT_FLASHED" or manifest.get("target") != "esp32s3" or manifest.get("idf_version") != PINNED_IDF:
        raise ValueError("No compatible successful build manifest. Build before flashing.")
    base = Path(manifest["build_directory"]).resolve()
    for name, expected in manifest["binary_sha256"].items():
        path = (base/name).resolve()
        if not path.is_relative_to(base) or sha256(path) != expected:
            raise ValueError(f"Firmware artifact changed or escapes build directory: {name}")
    return manifest


def export_evidence(engine, output_root, board_identity=None, firmware_manifest=None):
    """Create new immutable bundle, never overwrite an earlier session."""
    evidence = engine.last_g1_evidence or assess_g1(engine)
    directory = Path(output_root)/f"{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}_{uuid.uuid4().hex[:8]}"
    directory.mkdir(parents=True,exist_ok=False)
    journal = engine.diagnostic_journal or get_flight_recorder()
    events = journal.get_recent_events(limit=500)
    payloads = {
        "session_manifest.json":{"created_utc":utc_now(),"port":engine.port_name,
            "physical_transport":evidence["physical_transport"],"is_simulated":engine.is_simulated,
            "host":git_info(),"firmware_identity_scope":"HELLO reported version/UID; binary identity not authenticated"},
        "board_identity.json":board_identity or {"status":"PHYSICAL_INSPECTION_REQUIRED"},
        "firmware_build_manifest.json":firmware_manifest or {"status":"UNAVAILABLE","device_reported":evidence["capabilities"]},
        "usb_enumeration.json":[p.to_dict() for p in UsbDiscoveryDoctor().scan_ports()],
        "g1_protocol_summary.json":evidence,
        "g1_sample_integrity.json":{"samples":evidence["host_samples_accepted"],
            "mismatches":evidence["host_sample_value_errors"],"sha256":evidence["sha256_hash"],
            "first_mismatch":evidence["first_mismatch"]},
        "g1_telemetry.json":{"origin":"REPORTED_BY_FIRMWARE","value":evidence["telemetry"]},
        "g1_timing.json":{"origin":"DERIVED_HOST; CLOCK_ACCURACY_UNAVAILABLE",**evidence["timing"]},
    }
    for name,data in payloads.items():
        write_json(directory/name,data)
    (directory/"fault_events.jsonl").write_text("".join(json.dumps(e.to_dict() if hasattr(e,"to_dict") else e)+"\n" for e in events),encoding="utf-8")
    report = ["# AuscultaForge physical G1 acceptance",f"Result: {evidence['conclusion']}",
              f"Transport: {'SOFTWARE SIMULATION' if engine.is_simulated else 'physical CDC' if evidence['physical_transport'] else 'UNVERIFIED'}",
              "G0 board inspection and G1A physical boot: see board evidence; unavailable facts remain NOT_EXECUTED.",
              "G2 microphone and G3 acoustics: NOT_EXECUTED by this G1 test.",
              "| Gate | Result |","| --- | --- |"]
    report += [f"| {k} | {v} |" for k,v in evidence["gates"].items()]
    report += ["", "Host observations, firmware counters and unavailable measurements are separated in the JSON files.",
               "HELLO identifies compatible protocol/version, not a cryptographically authenticated firmware image."]
    (directory/"acceptance_report.md").write_text("\n\n".join(report)+"\n",encoding="utf-8")
    write_json(directory/"sha256_manifest.json",{p.name:sha256(p) for p in directory.iterdir() if p.is_file()})
    return directory


def physical_g1(port, output_root, board_identity=None, firmware_manifest=None):
    if port.upper() in ("SIMULATED","SIMULATED_ESP32_S3","LOOPBACK"):
        raise ValueError("Physical-only command rejects simulated transports.")
    engine = CanonicalSessionEngine(diagnostic_journal=get_flight_recorder())
    error = None
    try:
        caps = engine.connect(port,timeout_s=4).result(timeout=5)
        if type(engine.transport) is not UsbCdcAcmAdapter or engine.is_simulated:
            raise RuntimeError("Physical USB CDC adapter required")
        reported = f"{caps.firmware_version_major}.{caps.firmware_version_minor}.{caps.firmware_version_patch}"
        if firmware_manifest and reported != firmware_manifest["firmware_version"]:
            raise RuntimeError(f"Connected firmware {reported} differs from selected build {firmware_manifest['firmware_version']}")
        rom = (board_identity or {}).get("rom_identity", {})
        if rom.get("chip_mac") and caps.device_uid_low != int(rom["chip_mac"].replace(":","")[-8:],16):
            raise RuntimeError("CDC UID differs from the ROM-identified board; do not start acquisition")
        engine.start_acquisition(target_samples=480000,source_mode=1).result(timeout=5)
        deadline = time.monotonic()+15
        while engine.session.host_samples_accepted < 480000:
            if engine.state.value != "STREAMING":
                raise RuntimeError(f"Acquisition interrupted: {engine.state.value}")
            if time.monotonic() >= deadline:
                raise TimeoutError("480000 samples not received before deadline")
            time.sleep(0.01)
        engine.stop_acquisition().result(timeout=5)
    except Exception as exc:
        error = str(exc)
        engine.session.error_log.append(error)
    try:
        engine.last_g1_evidence = assess_g1(engine)
        if error:
            engine.last_g1_evidence["failure_reasons"].append(error)
        directory = export_evidence(engine,output_root,board_identity,firmware_manifest)
        return engine.last_g1_evidence, directory
    finally:
        engine.disconnect().result(timeout=5)
