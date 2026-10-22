"""AuscultaForge — Unit Tests for Signal Quality & Acoustic Diagnostics Doctor."""

from pathlib import Path
import numpy as np
import pytest

from pcg_app.diagnostics.flight_recorder import FlightRecorderJournal
from pcg_app.diagnostics.signal_doctor import SignalQualityDoctor


def test_signal_doctor_normal_signal(tmp_path: Path):
    """Verify clean 100 Hz sine wave produces healthy metrics without false alarms."""
    journal = FlightRecorderJournal(log_dir=tmp_path, enable_disk_persistence=False)
    doctor = SignalQualityDoctor(flight_recorder=journal)

    fs = 4000
    t = np.arange(4000) / fs
    clean_sine = (0.5 * np.sin(2 * np.pi * 100.0 * t)).astype(np.float32)

    snap = doctor.analyze_window(clean_sine, sample_rate_hz=fs)
    assert snap.is_evaluated is True
    assert snap.is_clipping is False
    assert snap.is_near_silence is False
    assert snap.is_excessive_dc is False
    assert len(snap.active_fault_codes) == 0
    assert snap.scientific_provenance["medical_diagnosis"] == "forbidden (Engineering quality assessment only)"


def test_signal_doctor_near_silence(tmp_path: Path):
    """Verify silence below -60 dBFS triggers AF-SIG-001."""
    journal = FlightRecorderJournal(log_dir=tmp_path, enable_disk_persistence=False)
    doctor = SignalQualityDoctor(flight_recorder=journal)

    zeros = np.zeros(4000, dtype=np.float32)
    snap = doctor.analyze_window(zeros, sample_rate_hz=4000)

    assert snap.is_near_silence is True
    assert "AF-SIG-001" in snap.active_fault_codes
    assert len(journal.get_recent_events(fault_code="AF-SIG-001")) == 1


def test_signal_doctor_clipping_detection(tmp_path: Path):
    """Verify rail contact (>= 0.999 FS) triggers AF-SIG-002."""
    journal = FlightRecorderJournal(log_dir=tmp_path, enable_disk_persistence=False)
    doctor = SignalQualityDoctor(flight_recorder=journal)

    clipped = np.ones(4000, dtype=np.float32) * 1.0
    snap = doctor.analyze_window(clipped, sample_rate_hz=4000)

    assert snap.is_clipping is True
    assert snap.clipping_hits == 4000
    assert "AF-SIG-002" in snap.active_fault_codes
    assert len(journal.get_recent_events(fault_code="AF-SIG-002")) == 1


def test_signal_doctor_dc_offset_detection(tmp_path: Path):
    """Verify DC offset > 10% FS triggers AF-SIG-003."""
    journal = FlightRecorderJournal(log_dir=tmp_path, enable_disk_persistence=False)
    doctor = SignalQualityDoctor(flight_recorder=journal)

    fs = 4000
    t = np.arange(4000) / fs
    biased = (0.25 + 0.1 * np.sin(2 * np.pi * 100.0 * t)).astype(np.float32)
    snap = doctor.analyze_window(biased, sample_rate_hz=fs)

    assert snap.is_excessive_dc is True
    assert "AF-SIG-003" in snap.active_fault_codes
    assert len(journal.get_recent_events(fault_code="AF-SIG-003")) == 1


def test_signal_doctor_insufficient_samples(tmp_path: Path):
    """Verify window with fewer than min_evaluation_samples returns is_evaluated=False."""
    journal = FlightRecorderJournal(log_dir=tmp_path, enable_disk_persistence=False)
    doctor = SignalQualityDoctor(flight_recorder=journal)

    tiny = np.zeros(32, dtype=np.float32)
    snap = doctor.analyze_window(tiny, sample_rate_hz=4000)

    assert snap.is_evaluated is False
    assert snap.scientific_provenance["status"] == "NOT_EVALUATED"
    assert len(journal.get_recent_events()) == 0
