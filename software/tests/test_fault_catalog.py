"""AuscultaForge — Unit Tests for Engineering Fault Catalog & Taxonomy."""

import re
import pytest

from pcg_app.diagnostics.fault_catalog import (
    FAULT_CATALOG,
    FaultDefinition,
    Severity,
    Subsystem,
    EvidenceOrigin,
    get_fault_definition,
    list_fault_definitions,
)


def test_fault_catalog_code_uniqueness():
    """Verify all fault codes are strictly unique across the system."""
    codes = [f.code for f in FAULT_CATALOG.values()]
    assert len(codes) == len(set(codes)), "Duplicate fault codes detected in catalog"


def test_fault_catalog_naming_convention():
    """Verify all fault codes match the canonical AF-XXX-NNN regex pattern."""
    pattern = re.compile(r"^AF-(USB|PRT|STR|SIG|DSP|FILE|APP)-\d{3}$")
    for code in FAULT_CATALOG:
        assert pattern.match(code), f"Fault code '{code}' violates standard naming convention"


def test_fault_catalog_completeness():
    """Verify each fault definition contains all required metadata and non-empty descriptions."""
    for code, fault in FAULT_CATALOG.items():
        assert fault.name and fault.name.isupper(), f"Fault name invalid in {code}"
        assert isinstance(fault.subsystem, Subsystem)
        assert isinstance(fault.severity, Severity)
        assert len(fault.description_en) > 10, f"English description too short in {code}"
        assert len(fault.description_tr) > 10, f"Turkish description too short in {code}"
        assert len(fault.possible_causes) > 0, f"Missing possible causes in {code}"
        assert len(fault.suggested_actions) > 0, f"Missing suggested actions in {code}"
        assert any("Hypothesis:" in c for c in fault.possible_causes), f"Causes must be labeled hypotheses in {code}"
        assert fault.primary_owner in ("Ozan (Module B)", "Ege (Module C)", "Joint (Module B/C)"), (
            f"Invalid primary owner '{fault.primary_owner}' in {code}"
        )


def test_fault_catalog_filtering():
    """Verify filtering by subsystem works correctly."""
    usb_faults = list_fault_definitions(Subsystem.USB)
    assert len(usb_faults) >= 8
    assert all(f.subsystem == Subsystem.USB for f in usb_faults)

    prt_faults = list_fault_definitions(Subsystem.PROTOCOL)
    assert len(prt_faults) >= 10
    assert all(f.subsystem == Subsystem.PROTOCOL for f in prt_faults)


def test_get_fault_definition():
    """Verify retrieval of specific definitions by code."""
    f = get_fault_definition("AF-USB-001")
    assert f is not None
    assert f.name == "NO_COMPATIBLE_DEVICE_DETECTED"
    assert f.subsystem == Subsystem.USB

    assert get_fault_definition("NONEXISTENT_CODE") is None
