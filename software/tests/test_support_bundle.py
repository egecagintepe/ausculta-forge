"""AuscultaForge — Unit Tests for Diagnostics Support Bundle Exporter."""

import json
from pathlib import Path
import zipfile
import pytest

from pcg_app.diagnostics.flight_recorder import FlightRecorderJournal
from pcg_app.diagnostics.support_bundle import DiagnosticsSupportBundleExporter


def test_support_bundle_export(tmp_path: Path):
    """Verify diagnostics ZIP package creation and privacy/ground-truth demarcation."""
    log_dir = tmp_path / "logs"
    out_dir = tmp_path / "exports"

    journal = FlightRecorderJournal(log_dir=log_dir, enable_disk_persistence=False)
    journal.record(
        fault_code="AF-USB-001",
        message="No compatible device found with token 0123456789abcdef0123456789abcdef",
    )

    exporter = DiagnosticsSupportBundleExporter(flight_recorder=journal)
    zip_path = exporter.create_bundle(
        output_dir=out_dir,
        device_runtime_state={"connected": False, "state": "absent", "auth_token": "secret_abc_123"},
        device_stats={"packets_received": 0, "crc_failures": 0},
        usb_descriptors=[{"port_name": "COM1", "description": "Standard Serial"}],
        is_simulation_run=True,
    )

    assert zip_path.exists()
    assert zip_path.suffix == ".zip"

    # Inspect zip contents
    with zipfile.ZipFile(zip_path, "r") as zf:
        namelist = zf.namelist()
        assert "system_info.json" in namelist
        assert "hardware_status.json" in namelist
        assert "fault_summary.json" in namelist
        assert "flight_recorder.jsonl" in namelist
        assert "g1_acceptance.json" in namelist
        assert "README_DIAGNOSTICS.md" in namelist

        # Verify no audio files included
        assert not any(n.endswith(".wav") for n in namelist)

        # Verify README ground truth demarcation
        readme_content = zf.read("README_DIAGNOSTICS.md").decode("utf-8")
        assert "**PHYSICAL_DEVICE_CONNECTED:** `NO`" in readme_content
        assert "**PHYSICAL_G1_VERIFIED:** `NOT_EXECUTED`" in readme_content
        assert "**SIMULATION_EXECUTED:** `YES`" in readme_content

        # Verify secrets redacted
        hw_content = zf.read("hardware_status.json").decode("utf-8")
        assert "secret_abc_123" not in hw_content
        assert "[REDACTED]" in hw_content
