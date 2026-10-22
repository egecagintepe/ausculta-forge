"""AuscultaForge — Canonical Structured Diagnostic Event Model.

Provides:
- Machine-readable DiagnosticEvent dataclass adhering strictly to the EEE495/496 schema.
- Event correlation tracking across connection and session timelines.
- Strict evidence provenance tagging (EvidenceOrigin).
- Monotonic vs UTC timebase separation.
- Event deduplication and aggregation.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
import json
import time
from typing import Any, Dict, List, Optional
import uuid

from .fault_catalog import (
    FaultDefinition,
    Severity,
    Subsystem,
    EvidenceOrigin,
    get_fault_definition,
)

SCHEMA_VERSION = "1.0.0"
SOFTWARE_VERSION = "0.1.0-alpha.1"


@dataclass(slots=True)
class DiagnosticEvent:
    """Canonical structured diagnostic event model."""
    event_id: str
    timestamp_utc: str
    host_monotonic_ns: int
    severity: Severity
    subsystem: Subsystem
    fault_code: str
    message: str
    source_type: str
    evidence_origin: EvidenceOrigin
    device_state: str
    schema_version: str = SCHEMA_VERSION
    session_id: Optional[str] = None
    connection_attempt_id: Optional[str] = None
    device_port: Optional[str] = None
    protocol_version: Optional[str] = "0.1"
    frame_sequence: Optional[int] = None
    first_sample_index: Optional[int] = None
    observed_value: Optional[Any] = None
    expected_value: Optional[Any] = None
    relevant_counter_snapshot: dict[str, Any] = field(default_factory=dict)
    possible_causes: list[str] = field(default_factory=list)
    suggested_actions: list[str] = field(default_factory=list)
    event_status: str = "active"  # "active" | "resolved" | "transient"
    correlation_id: Optional[str] = None
    software_version: str = SOFTWARE_VERSION
    occurrence_count: int = 1
    last_occurred_utc: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert event to serialized JSON-ready dictionary."""
        d = asdict(self)
        d["severity"] = self.severity.value if isinstance(self.severity, Severity) else str(self.severity)
        d["subsystem"] = self.subsystem.value if isinstance(self.subsystem, Subsystem) else str(self.subsystem)
        d["evidence_origin"] = (
            self.evidence_origin.value
            if isinstance(self.evidence_origin, EvidenceOrigin)
            else str(self.evidence_origin)
        )
        return d

    def to_json(self) -> str:
        """Serialize event to a single JSON line."""
        return json.dumps(self.to_dict(), default=str)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DiagnosticEvent:
        """Reconstruct event from serialized dictionary."""
        d = dict(data)
        if "severity" in d and isinstance(d["severity"], str):
            try:
                d["severity"] = Severity(d["severity"])
            except ValueError:
                d["severity"] = Severity.INFO
        if "subsystem" in d and isinstance(d["subsystem"], str):
            try:
                d["subsystem"] = Subsystem(d["subsystem"])
            except ValueError:
                d["subsystem"] = Subsystem.APP
        if "evidence_origin" in d and isinstance(d["evidence_origin"], str):
            try:
                d["evidence_origin"] = EvidenceOrigin(d["evidence_origin"])
            except ValueError:
                d["evidence_origin"] = EvidenceOrigin.OBSERVED_HOST

        # Ensure lists are lists
        d["possible_causes"] = list(d.get("possible_causes", []))
        d["suggested_actions"] = list(d.get("suggested_actions", []))
        d["relevant_counter_snapshot"] = dict(d.get("relevant_counter_snapshot", {}))

        return cls(**d)

    @classmethod
    def create(
        cls,
        fault_code: str,
        message: Optional[str] = None,
        subsystem: Optional[Subsystem] = None,
        severity: Optional[Severity] = None,
        source_type: str = "device",
        evidence_origin: EvidenceOrigin = EvidenceOrigin.OBSERVED_HOST,
        device_state: str = "absent",
        session_id: Optional[str] = None,
        connection_attempt_id: Optional[str] = None,
        device_port: Optional[str] = None,
        protocol_version: Optional[str] = "0.1",
        frame_sequence: Optional[int] = None,
        first_sample_index: Optional[int] = None,
        observed_value: Optional[Any] = None,
        expected_value: Optional[Any] = None,
        counter_snapshot: Optional[dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
        event_status: str = "active",
        custom_causes: Optional[list[str]] = None,
        custom_actions: Optional[list[str]] = None,
    ) -> DiagnosticEvent:
        """Factory helper creating event populated from fault catalog defaults."""
        fault_def = get_fault_definition(fault_code)
        now_utc = datetime.now(timezone.utc).isoformat()
        mono_ns = time.monotonic_ns()
        event_id = f"af-evt-{uuid.uuid4().hex[:12]}"

        res_subsystem = subsystem or (fault_def.subsystem if fault_def else Subsystem.APP)
        res_severity = severity or (fault_def.severity if fault_def else Severity.INFO)
        res_message = message or (fault_def.description_en if fault_def else f"Fault event: {fault_code}")
        res_causes = custom_causes if custom_causes is not None else (list(fault_def.possible_causes) if fault_def else [])
        res_actions = custom_actions if custom_actions is not None else (list(fault_def.suggested_actions) if fault_def else [])

        return cls(
            event_id=event_id,
            timestamp_utc=now_utc,
            host_monotonic_ns=mono_ns,
            severity=res_severity,
            subsystem=res_subsystem,
            fault_code=fault_code,
            message=res_message,
            source_type=source_type,
            evidence_origin=evidence_origin,
            device_state=device_state,
            session_id=session_id,
            connection_attempt_id=connection_attempt_id,
            device_port=device_port,
            protocol_version=protocol_version,
            frame_sequence=frame_sequence,
            first_sample_index=first_sample_index,
            observed_value=observed_value,
            expected_value=expected_value,
            relevant_counter_snapshot=counter_snapshot or {},
            possible_causes=res_causes,
            suggested_actions=res_actions,
            event_status=event_status,
            correlation_id=correlation_id or connection_attempt_id or session_id,
            occurrence_count=1,
            last_occurred_utc=now_utc,
        )
