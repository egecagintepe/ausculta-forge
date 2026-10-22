"""AuscultaForge — Engineering Support Bundle Exporter.

Packages sanitized diagnostic telemetry into a standalone ZIP archive for team debugging:
- flight_recorder.jsonl (Sanitized and token-redacted event journal)
- system_info.json (OS, Python, AuscultaForge and protocol versions)
- hardware_status.json (Enumerated USB descriptors & verified capabilities)
- fault_summary.json (Active faults & correlation engine report)
- counters_snapshot.json (Transport, DMA, sequence & display counters)
- g1_acceptance.json (Physical G1 status or NOT_EXECUTED)
- README_DIAGNOSTICS.md (Human-readable markdown incident summary)

STRICT PRIVACY & GROUND TRUTH CONSTRAINTS:
1. Authentication secrets and tokens are strictly redacted.
2. Raw patient audio recordings (.wav) are NEVER included without separate consent.
3. Explicit Ground Truth Demarcation:
   - PHYSICAL_DEVICE_CONNECTED: YES / NO / UNKNOWN
   - PHYSICAL_G1_VERIFIED: YES / NO / NOT_EXECUTED
   - SIMULATION_EXECUTED: YES / NO
4. No automatic external uploads; bundle is generated locally on user demand.
"""

from __future__ import annotations

from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import platform
import sys
import zipfile
from typing import Any, Dict, List, Optional

from .fault_catalog import Subsystem, Severity, EvidenceOrigin
from .event_model import DiagnosticEvent, SCHEMA_VERSION, SOFTWARE_VERSION
from .flight_recorder import FlightRecorderJournal, redact_dict, redact_sensitive_data
from .correlation_engine import RootCauseCorrelationEngine, CorrelationReport


class DiagnosticsSupportBundleExporter:
    """Produces sanitized, portable diagnostics zip packages."""

    def __init__(
        self,
        flight_recorder: FlightRecorderJournal,
        correlation_engine: Optional[RootCauseCorrelationEngine] = None,
    ) -> None:
        self.flight_recorder = flight_recorder
        self.correlation_engine = correlation_engine or RootCauseCorrelationEngine(flight_recorder)

    def create_bundle(
        self,
        output_dir: Path,
        device_runtime_state: Optional[dict[str, Any]] = None,
        device_stats: Optional[dict[str, Any]] = None,
        usb_descriptors: Optional[list[dict[str, Any]]] = None,
        g1_report: Optional[dict[str, Any]] = None,
        is_simulation_run: bool = False,
    ) -> Path:
        """Generate and save diagnostics zip archive to output_dir."""
        output_dir = Path(output_dir).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        now_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        zip_filename = f"auscultaforge_diagnostics_{now_str}.zip"
        zip_path = output_dir / zip_filename

        # Correlate recent incidents
        is_dev_connected = bool(device_runtime_state and device_runtime_state.get("connected"))
        corr_report = self.correlation_engine.evaluate_incidents(
            is_device_connected=is_dev_connected,
            is_streaming=bool(device_runtime_state and device_runtime_state.get("state") == "streaming"),
        )

        # Ground truth status
        phys_connected = "YES" if is_dev_connected and not is_simulation_run else ("NO" if not is_dev_connected else "UNKNOWN")
        phys_g1 = "YES" if (g1_report and g1_report.get("is_physical") and g1_report.get("verdict") == "PASS") else ("NOT_EXECUTED" if not g1_report else "NO")
        sim_executed = "YES" if is_simulation_run or (g1_report and not g1_report.get("is_physical", True)) else "NO"

        # System metadata
        sys_info = {
            "schema_version": SCHEMA_VERSION,
            "software_version": SOFTWARE_VERSION,
            "protocol_version": "0.1",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "platform": platform.platform(),
            "os_name": os.name,
            "python_version": sys.version,
            "machine": platform.machine(),
            "processor": platform.processor(),
        }

        # Hardware status
        hw_status = {
            "physical_device_connected": phys_connected,
            "runtime_state": redact_dict(device_runtime_state or {}),
            "usb_descriptors": [redact_dict(d) for d in (usb_descriptors or [])],
        }

        # Events
        events = self.flight_recorder.get_recent_events(limit=500)
        events_jsonl = "\n".join(e.to_json() for e in events)

        # Markdown summary report
        md_report = self._build_markdown_summary(
            phys_connected=phys_connected,
            phys_g1=phys_g1,
            sim_executed=sim_executed,
            sys_info=sys_info,
            corr_report=corr_report,
            events_count=len(events),
        )

        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("system_info.json", json.dumps(sys_info, indent=2))
            zf.writestr("hardware_status.json", json.dumps(hw_status, indent=2))
            zf.writestr("fault_summary.json", json.dumps(corr_report.to_dict(), indent=2))
            zf.writestr("counters_snapshot.json", json.dumps(redact_dict(device_stats or {}), indent=2))
            zf.writestr("flight_recorder.jsonl", events_jsonl)
            zf.writestr("g1_acceptance.json", json.dumps(g1_report or {"status": "NOT_EXECUTED"}, indent=2))
            zf.writestr("README_DIAGNOSTICS.md", md_report)

        return zip_path

    def _build_markdown_summary(
        self,
        phys_connected: str,
        phys_g1: str,
        sim_executed: str,
        sys_info: dict[str, Any],
        corr_report: CorrelationReport,
        events_count: int,
    ) -> str:
        """Construct human-readable diagnostic incident overview."""
        lines = [
            "# AuscultaForge Engineering Diagnostics Support Bundle",
            f"Generated: {sys_info['generated_at_utc']}",
            f"Software Version: {sys_info['software_version']} (Protocol v{sys_info['protocol_version']})",
            "",
            "## 1. Physical Hardware Ground Truth Demarcation",
            f"- **PHYSICAL_DEVICE_CONNECTED:** `{phys_connected}`",
            f"- **PHYSICAL_G1_VERIFIED:** `{phys_g1}`",
            f"- **SIMULATION_EXECUTED:** `{sim_executed}`",
            "",
            "## 2. Root-Cause Correlation Diagnosis",
            f"- **Case Identifier:** `{corr_report.case_id}`",
            f"- **Summary:** {corr_report.summary}",
            f"- **Active Fault Count:** {corr_report.active_incident_count}",
            "",
            "### Ranked Troubleshooting Hypotheses",
        ]

        for h in corr_report.ranked_hypotheses:
            lines.extend([
                f"#### Rank {h.rank}: {h.title} [{h.confidence} CONFIDENCE]",
                f"- **Subsystem:** `{h.subsystem.value}` | **Primary Owner:** `{h.primary_owner}`",
                f"- **Evidence Summary:** {h.evidence_summary}",
                "- **Checklist:**",
            ])
            for step in h.recommended_checklist:
                lines.append(f"  {step}")
            lines.append("")

        lines.extend([
            "## 3. Host System Environment",
            f"- **Platform:** {sys_info['platform']}",
            f"- **Python:** {sys_info['python_version'].split()[0]}",
            f"- **Architecture:** {sys_info['machine']}",
            f"- **Flight Recorder Records:** {events_count} event(s) in `flight_recorder.jsonl`",
            "",
            "---",
            "*Note: This diagnostic bundle contains sanitized engineering telemetry. Raw audio recordings (.wav) and authentication secrets are excluded.*",
        ])
        return "\n".join(lines)
