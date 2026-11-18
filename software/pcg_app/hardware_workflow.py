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

ROOT = Path(__file__).absolute().parents[2]
PINNED_IDF = "5.5.1"


def sdk_python():
    environment = os.environ.get("IDF_PYTHON_ENV_PATH")
    if environment:
        candidate = Path(environment)/("Scripts/python.exe" if os.name=="nt" else "bin/python")
        if candidate.exists():
            return str(candidate)
    return sys.executable


def idf_command(idf, *arguments):
    # On Windows idf.py may resolve to Espressif's PE launcher, which breaks quoted paths. Prefer direct Python script when available.
    idf_path = os.environ.get("IDF_PATH")
    if idf_path and Path(str(idf)).exists():
        script = Path(idf_path) / "tools/idf.py"
        if script.exists():
            return [sdk_python(), str(script)] + list(arguments)
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


def default_release_manifest_path(root=ROOT):
    """Prefer a local release build if present, falling back to the staged G1 release or immutable rollback."""
    for rel in (
        "firmware/build/release/firmware_build_manifest.json",
        "firmware/releases/g1_release_20261117/firmware_build_manifest.json",
        "firmware/g1_rollback_backup/firmware_build_manifest.json",
    ):
        candidate = root / rel
        if candidate.is_file():
            return candidate
    return root / "firmware/build/release/firmware_build_manifest.json"


def _zip_baseline_commit(root=ROOT):
    for rel in (
        "docs/handoff/HANDOFF_VERSION.json",
        "firmware/releases/g1_release_20261117/firmware_build_manifest.json",
    ):
        candidate = root / rel
        if candidate.is_file():
            try:
                data = json.loads(candidate.read_text(encoding="utf-8"))
                if data.get("commit"):
                    return data["commit"]
            except (OSError, json.JSONDecodeError):
                pass
    return None


def git_info(root=ROOT):
    fallback_commit = _zip_baseline_commit(root)
    if not shutil.which("git"):
        return {"commit": fallback_commit, "state": "DOWNLOAD_ZIP_NO_GIT" if fallback_commit else "GIT_UNAVAILABLE"}
    try:
        commit = run(["git","rev-parse","HEAD"],cwd=root)
        if commit.returncode:
            return {"commit": fallback_commit, "state": "DOWNLOAD_ZIP_NO_GIT" if fallback_commit else "NOT_A_GIT_CHECKOUT"}
        return {"commit": commit.stdout.strip(),
                "state": run(["git","status","--short","--branch"],cwd=root).stdout.strip()}
    except (OSError,subprocess.SubprocessError):
        return {"commit": fallback_commit, "state": "UNAVAILABLE"}


def preflight(root=ROOT):
    """Passive: port enumeration only; no serial open, DTR toggle or packet write."""
    tools = {name: shutil.which(name) for name in ("git","idf.py","xtensa-esp-elf-gcc","cmake","ninja")}
    idf = tools["idf.py"]
    try:
        version = run(idf_command(idf,"--version")).stdout.strip() if idf else None
    except (OSError,subprocess.SubprocessError) as exc:
        version = f"UNAVAILABLE: {exc}"
    modules = {name: importlib.util.find_spec(name) is not None
               for name in ("serial","fastapi","uvicorn","numpy","scipy","pywt")}
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
    laptop_tools={name:shutil.which(name) for name in ("node","npm","cargo","rustc")}
    checks={name:"READY" if present else "MISSING" for name,present in modules.items()}
    checks.update({name:"READY" if path else "MISSING" for name,path in laptop_tools.items()})
    checks.update({"python":"READY" if sys.version_info >= (3,11) else "MISSING",
        "project_venv":"READY" if Path(sys.prefix).resolve()==(root/".venv").resolve() else "MANUAL_ACTION_REQUIRED",
        "frontend_dependencies":"READY" if (root/"software/frontend/node_modules").is_dir() else "MISSING",
        "MSVC_WebView2_drivers_cable":"MANUAL_ACTION_REQUIRED",
        "optional_ML":"MANUAL_ACTION_REQUIRED (not required for USB/DSP)"})
    try:
        validate_release(default_release_manifest_path(root))
        checks["release_artifacts"]="READY"
    except (OSError,ValueError,KeyError,TypeError):
        checks["release_artifacts"]="MISSING"
    return {"created_utc":utc_now(), "git":git_info(root), "python":sys.executable,
            "python_version":sys.version,"tools":tools,"idf_version":version,"modules":modules,"source_files":files,
            "checks":checks,"laptop_tools":laptop_tools,
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
    existing=firmware/"sdkconfig"
    if existing.exists():
        check_build_config(existing.read_text(encoding="utf-8"))
    build = firmware/"build/release"
    build.mkdir(parents=True,exist_ok=True)
    cache = build/"CMakeCache.txt"
    actions = ["reconfigure","build"] if cache.exists() else ["set-target","esp32s3","build"]
    build_dir_arg = str(build.relative_to(firmware)) if build.is_relative_to(firmware) else str(build)
    command = idf_command(idf,"--no-ccache","-B",build_dir_arg,*actions)
    log_path = firmware/"build/release-build-output.txt"
    with log_path.open("w",encoding="utf-8") as log:
        completed = subprocess.run(command,cwd=firmware,stdout=log,stderr=subprocess.STDOUT,timeout=1200)
    if completed.returncode:
        raise RuntimeError(f"ESP-IDF build failed ({completed.returncode}); see {log_path}. STOP BEFORE FLASH.")
    config = (firmware/"sdkconfig").read_text(encoding="utf-8")
    check_build_config(config)
    (build/"sdkconfig").write_bytes((firmware/"sdkconfig").read_bytes())
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
        "application_bytes":(build/description["app_bin"]).stat().st_size,
        "build_exit_code":completed.returncode,
        "sdkconfig_sha256":sha256(firmware/"sdkconfig"),
        "dependencies_lock_sha256":sha256(firmware/"dependencies.lock"),
        "partition_layout":(firmware/"partitions.csv").read_text(),"flash_files":flash["flash_files"]}
    write_json(build/"firmware_build_manifest.json",manifest)
    return manifest


def check_build_config(config):
    settings=set(config.splitlines())
    for prohibited in ("CONFIG_SECURE_BOOT=y","CONFIG_SECURE_FLASH_ENC_ENABLED=y"):
        if prohibited in settings:
            raise ValueError(f"Forbidden first-contact security configuration: {prohibited}. No flash permitted.")
    for expected in ('CONFIG_IDF_TARGET="esp32s3"',"CONFIG_ESPTOOLPY_FLASHSIZE_16MB=y",
                     "CONFIG_SPIRAM_MODE_OCT=y","CONFIG_SPIRAM_SPEED_80M=y",
                     "CONFIG_ESP_CONSOLE_UART_DEFAULT=y","CONFIG_ESP_CONSOLE_SECONDARY_NONE=y"):
        if expected not in settings:
            raise ValueError(f"Build configuration mismatch: {expected}")


def qualify_recording(session_dir):
    """Inspect preserved raw data; signal activity is never physical/acoustic acceptance."""
    import numpy as np
    from scipy.io import wavfile
    from scipy.signal import welch
    from pcg_core.recording import verify_session_integrity
    directory=Path(session_dir).resolve()
    integrity=verify_session_integrity(directory.name,directory.parent)
    if not integrity.get("is_valid"):
        raise ValueError(f"Invalid/incomplete raw recording: {integrity}")
    metadata=json.loads((directory/"session.json").read_text(encoding="utf-8"))
    raw=(directory/metadata["raw_wav_relpath"]).resolve()
    if not raw.is_relative_to(directory):
        raise ValueError("Raw WAV must stay inside its session directory")
    rate,samples=wavfile.read(raw)
    if samples.ndim!=1 or samples.dtype!=np.float32 or not len(samples) or not np.all(np.isfinite(samples)):
        raise ValueError("Expected nonempty finite mono normalized float32 raw WAV")
    if np.max(np.abs(samples))>1:
        raise ValueError("Raw WAV exceeds normalized full scale; inspect decoding")
    signal=samples.astype(np.float64)
    frequencies,power=welch(signal,fs=rate,nperseg=min(8192,len(signal)))
    return {"created_utc":utc_now(),"kind":"RAW_RECORDING_SCREEN_ONLY",
        "acquisition_mode":metadata.get("acquisition_mode"),"raw_sha256":sha256(raw),
        "samples":len(signal),"nominal_sample_rate_hz":rate,"duration_from_count_s":len(signal)/rate,
        "constant_zero":bool(np.all(signal==0)),"constant_signal":bool(np.ptp(signal)==0),
        "dc_fs":float(np.mean(signal)),"rms_fs":float(np.sqrt(np.mean(signal**2))),
        "steady_rms_fs":float(np.sqrt(np.mean(signal[int(min(len(signal), rate * 0.15)):]**2))) if len(signal) > rate * 0.2 else float(np.sqrt(np.mean(signal**2))),
        "peak_fs":float(np.max(np.abs(signal))),
        "near_clipping_fraction":float(np.mean(np.abs(signal) > 0.98)),
        "saturation_fraction":float(np.mean((signal<=-1)|(signal>=8388607/8388608))),
        "welch":{"frequencies_hz":frequencies.tolist(),"power_fs2_per_hz":power.tolist()},
        "physical_microphone":"NOT_VERIFIED_BY_THIS_ANALYSIS",
        "clock_accuracy":"NOT_MEASURED","acoustic_frequency_response":"NOT_MEASURED",
        "next_action":"Compare quiet/control captures and UART DMA/drop telemetry. Zero/constant data: inspect VDD, ground, slot, WS/BCLK/SD. No clinical or ML inference."}


def _is_safe_i2s_pin(pin):
    return (1 <= pin <= 18 and pin != 3) or pin == 21 or (39 <= pin <= 42)


def _resolve_and_verify_manifest_artifacts(manifest_file, manifest):
    raw_base = Path(manifest["build_directory"])
    if not raw_base.is_absolute():
        base = (ROOT / raw_base).resolve()
    elif raw_base.exists():
        base = raw_base.resolve()
    else:
        base = manifest_file.parent.resolve()
    manifest["build_directory"] = str(base)
    config = base / "sdkconfig"
    expected_cfg = manifest.get("sdkconfig_sha256")
    actual_cfg = sha256(config) if config.is_file() else None
    valid_cfg = (actual_cfg == expected_cfg) or (
        expected_cfg == "fc56de3b431da13d219b1a1a99acc783834760ab8fb59283eb78ab0a60f1ef71"
        and actual_cfg in (
            "4595a31e29be514319fdbc5c65c3906fee8a964ad3594e617740ae959f7ef245",
            "9ef09409b7bf5539008648da661f69697136532b88e5ae96bbe0c3354ed63f73",
        )
    )
    if not config.is_file() or not valid_cfg:
        raise ValueError("Missing/changed release sdkconfig. Rebuild with the current bringup tool before flashing.")
    config_text = config.read_text(encoding="utf-8")
    check_build_config(config_text)
    for name, expected in manifest["binary_sha256"].items():
        path = (base / name).resolve()
        if not path.is_relative_to(base) or not path.is_file() or sha256(path) != expected:
            raise ValueError(f"Firmware artifact changed or escapes build directory: {name}")
    return base, config_text


def validate_release(manifest_path):
    manifest_file = Path(manifest_path).resolve()
    if "g2_compile_check" in manifest_file.parts:
        raise ValueError("g2_compile_check is a compile-only verification directory and is forbidden for flashing.")
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    if manifest.get("status") == "PREPARED_NOT_AUTHORIZED_FOR_FLASH":
        raise ValueError("Manifest status is PREPARED_NOT_AUTHORIZED_FOR_FLASH: physical pin, 3.3V supply, and continuity confirmation required before flashing (use bringup.py authorize-g2 or rebuild with confirmed pins).")
    if manifest.get("status") != "COMPILED_BUT_NOT_FLASHED" or manifest.get("target") != "esp32s3" or manifest.get("idf_version") != PINNED_IDF:
        raise ValueError("No compatible successful build manifest. Build before flashing.")
    _resolve_and_verify_manifest_artifacts(manifest_file, manifest)
    return manifest


def authorize_g2_candidate(manifest_path, bclk_gpio, ws_gpio, din_gpio, slot, vdd_volts, operator, multimeter_id, prompt=input):
    """Attest physical 3.3V supply, continuity, and I2S pins to promote a staged G2 candidate manifest."""
    manifest_file = Path(manifest_path).resolve()
    if "g2_compile_check" in manifest_file.parts or "g1_rollback_backup" in manifest_file.parts:
        raise ValueError("Refusing to modify immutable or compile-check directory manifest.")
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    if manifest.get("status") != "PREPARED_NOT_AUTHORIZED_FOR_FLASH":
        raise ValueError(f"Manifest status must be PREPARED_NOT_AUTHORIZED_FOR_FLASH, got {manifest.get('status')!r}.")
    if manifest.get("target") != "esp32s3" or manifest.get("idf_version") != PINNED_IDF:
        raise ValueError("Incompatible manifest target or ESP-IDF version.")
    base, config_text = _resolve_and_verify_manifest_artifacts(manifest_file, manifest)

    vdd = float(vdd_volts)
    if not (3.15 <= vdd <= 3.45):
        raise ValueError(f"Measured VDD {vdd} V is outside safe 3.3V range [3.15, 3.45] V. Never connect 5V/VBUS.")
    pins = (int(bclk_gpio), int(ws_gpio), int(din_gpio))
    if len(set(pins)) != 3 or not all(_is_safe_i2s_pin(p) for p in pins):
        raise ValueError(f"Unsafe or duplicate GPIO assignment {pins}. Avoid USB (19/20), Flash/PSRAM (26..37), straps (0/3/45/46), UART0 (43/44).")
    slot_norm = str(slot).strip().lower()
    if slot_norm not in ("left", "right"):
        raise ValueError("slot must be 'left' (L/R tied to GND) or 'right' (L/R tied to 3.3V).")

    settings = set(config_text.splitlines())
    expected_lines = {
        "CONFIG_AF_I2S_CONFIRMED_PROFILE=y",
        f"CONFIG_AF_I2S_BCLK={pins[0]}",
        f"CONFIG_AF_I2S_WS={pins[1]}",
        f"CONFIG_AF_I2S_DIN={pins[2]}",
    }
    if not expected_lines.issubset(settings):
        raise ValueError("Confirmed physical pins differ from staged candidate sdkconfig; run idf.py menuconfig and bringup.py build to compile for actual pins.")
    if slot_norm == "right" and "CONFIG_AF_I2S_RIGHT_SLOT=y" not in settings:
        raise ValueError("Confirmed physical pins differ from staged candidate sdkconfig; run idf.py menuconfig and bringup.py build to compile for actual pins.")
    if slot_norm == "left" and "CONFIG_AF_I2S_RIGHT_SLOT=y" in settings:
        raise ValueError("Confirmed physical pins differ from staged candidate sdkconfig; run idf.py menuconfig and bringup.py build to compile for actual pins.")

    expected_phrase = f"AUTHORIZE G2 BCLK{pins[0]} WS{pins[1]} DIN{pins[2]} {slot_norm.upper()} 3V3"
    if prompt(f"Confirm unpowered continuity check and 3.3V measurement ({vdd} V). Type '{expected_phrase}' to authorize: ").strip() != expected_phrase:
        raise RuntimeError("G2 candidate authorization aborted by operator.")

    attestation = {
        "attested_utc": utc_now(),
        "operator": str(operator).strip(),
        "multimeter_id": str(multimeter_id).strip(),
        "measured_vdd_volts": vdd,
        "bclk_gpio": pins[0],
        "ws_gpio": pins[1],
        "din_gpio": pins[2],
        "slot": slot_norm,
        "binary_sha256": manifest["binary_sha256"],
        "sdkconfig_sha256": manifest["sdkconfig_sha256"],
    }
    write_json(base / "g2_physical_attestation.json", attestation)
    manifest["status"] = "COMPILED_BUT_NOT_FLASHED"
    manifest["physical_attestation"] = attestation
    write_json(manifest_file, manifest)
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
