"""AuscultaForge — Diagnostics & Flight Recorder Subsystem.

Provides:
- Versioned Fault Catalog & Taxonomy
- Canonical Structured Event Model
- Persistent Flight Recorder Journal (JSONL & in-memory ring)
- Platform-Aware Real USB Discovery Doctor
- Signal Quality & Acoustic Anomaly Diagnostics
- Deterministic Root-Cause Correlation Engine
- Engineering Support Bundle Exporter
- Automated Fault Injection Laboratory
"""

from .fault_catalog import (
    FaultDefinition,
    Severity,
    Subsystem,
    EvidenceOrigin,
    FAULT_CATALOG,
    get_fault_definition,
    list_fault_definitions,
)

__all__ = [
    "FaultDefinition",
    "Severity",
    "Subsystem",
    "EvidenceOrigin",
    "FAULT_CATALOG",
    "get_fault_definition",
    "list_fault_definitions",
]
