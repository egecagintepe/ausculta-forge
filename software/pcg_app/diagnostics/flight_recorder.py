"""AuscultaForge — Persistent Diagnostic Flight Recorder Journal.

Thread-safe, non-blocking persistent JSONL diagnostic journal with:
- Asynchronous background disk persistence (never blocks 48 kHz acquisition)
- Bounded in-memory circular recent-event cache for low-latency UI queries
- Size-based automatic log rotation (e.g. 5 MB max per file, 5 backups)
- Repetitive event deduplication and occurrence counting
- Automatic redaction of authentication secrets, tokens, and PII
- Safe restart persistence recovery from existing journal files
- Fault-tolerant fallback: disk errors never interrupt live acquisition
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
import queue
import re
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from .event_model import DiagnosticEvent, Severity, Subsystem, EvidenceOrigin

logger = logging.getLogger("auscultaforge.flight_recorder")

# Secret redaction patterns
_TOKEN_PATTERN = re.compile(r"([0-9a-fA-F]{32,64}|ey[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,})")
_AUTH_HEADER_PATTERN = re.compile(r"(X-AuscultaForge-Auth|Authorization|Bearer|token|secret)[:=\s]+([^\s,;]+)", re.IGNORECASE)


def redact_sensitive_data(text: str) -> str:
    """Redact authentication tokens, secrets, and private keys from string."""
    if not text:
        return text
    redacted = _AUTH_HEADER_PATTERN.sub(r"\1: [REDACTED_SECRET]", text)
    redacted = _TOKEN_PATTERN.sub("[REDACTED_TOKEN]", redacted)
    return redacted


def redact_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Recursively sanitize dictionary removing secrets and auth tokens."""
    clean: dict[str, Any] = {}
    for k, v in data.items():
        k_lower = str(k).lower()
        if any(sec in k_lower for sec in ("token", "secret", "auth", "password", "key")):
            clean[k] = "[REDACTED]"
        elif isinstance(v, dict):
            clean[k] = redact_dict(v)
        elif isinstance(v, str):
            clean[k] = redact_sensitive_data(v)
        elif isinstance(v, list):
            clean[k] = [
                redact_dict(item) if isinstance(item, dict)
                else redact_sensitive_data(item) if isinstance(item, str)
                else item
                for item in v
            ]
        else:
            clean[k] = v
    return clean


class FlightRecorderJournal:
    """Thread-safe persistent diagnostic event journal."""

    def __init__(
        self,
        log_dir: Optional[Path | str] = None,
        max_file_size_bytes: int = 5 * 1024 * 1024,  # 5 MB
        max_backup_files: int = 5,
        in_memory_capacity: int = 500,
        dedup_window_seconds: float = 2.0,
        enable_disk_persistence: bool = True,
    ) -> None:
        if log_dir is None:
            import tempfile
            self.log_dir = Path(tempfile.gettempdir()) / "ausculta_forge_logs"
        else:
            self.log_dir = Path(log_dir).resolve()
        self.max_file_size_bytes = max_file_size_bytes
        self.max_backup_files = max_backup_files
        self.in_memory_capacity = in_memory_capacity
        self.dedup_window_seconds = dedup_window_seconds
        self.enable_disk_persistence = enable_disk_persistence

        self.journal_path = self.log_dir / "flight_recorder.jsonl"
        self._lock = threading.RLock()
        self._recent_events: list[DiagnosticEvent] = []
        self._last_event_by_key: dict[str, tuple[DiagnosticEvent, float]] = {}

        # Non-blocking async queue
        self._write_queue: queue.Queue[Optional[DiagnosticEvent]] = queue.Queue(maxsize=1000)
        self._worker_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._disk_available: bool = True

        if self.enable_disk_persistence:
            try:
                self.log_dir.mkdir(parents=True, exist_ok=True)
                self._recover_recent_from_disk()
            except Exception as e:
                logger.warning(f"Could not initialize flight recorder directory {self.log_dir}: {e}")
                self._disk_available = False

            self._start_worker()

    def _start_worker(self) -> None:
        """Start daemon worker thread draining queued events to JSONL disk storage."""
        if not self._disk_available or not self.enable_disk_persistence:
            return
        self._stop_event.clear()
        self._worker_thread = threading.Thread(
            target=self._persistence_worker_loop,
            daemon=True,
            name="FlightRecorderPersistenceWorker",
        )
        self._worker_thread.start()

    def record_event(self, event: DiagnosticEvent) -> DiagnosticEvent:
        """Submit a diagnostic event to the flight recorder.

        Non-blocking: Enqueues to in-memory buffer immediately and passes to
        background thread for disk storage. Automatically aggregates duplicates.
        """
        # Sanitize event message and metadata
        event.message = redact_sensitive_data(event.message)
        event.relevant_counter_snapshot = redact_dict(event.relevant_counter_snapshot)

        now_mono = time.monotonic()
        dedup_key = f"{event.fault_code}:{event.source_type}:{event.message}"

        with self._lock:
            # Check for repetition within dedup window
            if dedup_key in self._last_event_by_key:
                last_evt, last_time = self._last_event_by_key[dedup_key]
                if (now_mono - last_time) <= self.dedup_window_seconds:
                    last_evt.occurrence_count += 1
                    last_evt.last_occurred_utc = event.timestamp_utc
                    self._last_event_by_key[dedup_key] = (last_evt, now_mono)
                    return last_evt

            # New unique event
            self._recent_events.append(event)
            self._last_event_by_key[dedup_key] = (event, now_mono)

            # Cap in-memory list
            if len(self._recent_events) > self.in_memory_capacity:
                self._recent_events.pop(0)

        # Enqueue for disk persistence without blocking
        if self.enable_disk_persistence and self._disk_available:
            try:
                self._write_queue.put_nowait(event)
            except queue.Full:
                logger.warning("Flight recorder write queue full; dropping event from disk queue to protect acquisition.")

        return event

    def record(
        self,
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
        possible_causes: Optional[list[str]] = None,
        suggested_actions: Optional[list[str]] = None,
    ) -> DiagnosticEvent:
        """Convenience method constructing and recording a DiagnosticEvent in one call."""
        actual_causes = custom_causes or possible_causes
        actual_actions = custom_actions or suggested_actions
        evt = DiagnosticEvent.create(
            fault_code=fault_code,
            message=message,
            subsystem=subsystem,
            severity=severity,
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
            counter_snapshot=counter_snapshot,
            correlation_id=correlation_id,
            event_status=event_status,
            custom_causes=actual_causes,
            custom_actions=actual_actions,
        )
        return self.record_event(evt)

    def get_recent_events(
        self,
        limit: int = 100,
        subsystem: Optional[Subsystem] = None,
        severity: Optional[Severity] = None,
        fault_code: Optional[str] = None,
        correlation_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> list[DiagnosticEvent]:
        """Query recent in-memory events with high-performance filtering."""
        with self._lock:
            events = list(self._recent_events)

        filtered: list[DiagnosticEvent] = []
        for e in reversed(events):
            if subsystem is not None and e.subsystem != subsystem:
                continue
            if severity is not None and e.severity != severity:
                continue
            if fault_code is not None and e.fault_code != fault_code:
                continue
            if correlation_id is not None and e.correlation_id != correlation_id:
                continue
            if session_id is not None and e.session_id != session_id:
                continue
            filtered.append(e)
            if len(filtered) >= limit:
                break

        return list(reversed(filtered))

    def get_active_faults(self) -> list[DiagnosticEvent]:
        """Return list of unresolved / active fault events."""
        with self._lock:
            return [e for e in self._recent_events if e.event_status == "active" and e.severity in (Severity.WARNING, Severity.ERROR, Severity.CRITICAL)]

    def resolve_fault(self, fault_code: str, resolution_message: Optional[str] = None) -> int:
        """Mark active faults with given code as resolved."""
        count = 0
        with self._lock:
            for e in self._recent_events:
                if e.fault_code == fault_code and e.event_status == "active":
                    e.event_status = "resolved"
                    count += 1
        return count

    def clear_in_memory(self) -> None:
        """Clear in-memory ring buffer (does not delete rotated disk files)."""
        with self._lock:
            self._recent_events.clear()
            self._last_event_by_key.clear()

    # --------------------------------------------------------------------------
    # Background Disk Persistence & Rotation Worker
    # --------------------------------------------------------------------------
    def _persistence_worker_loop(self) -> None:
        """Background thread writing queued events to JSONL."""
        batch: list[DiagnosticEvent] = []
        while not self._stop_event.is_set():
            try:
                # Wait for next item
                item = self._write_queue.get(timeout=0.25)
                if item is None:
                    break
                batch.append(item)

                # Drain any additional pending items up to 50
                while len(batch) < 50:
                    try:
                        extra = self._write_queue.get_nowait()
                        if extra is None:
                            break
                        batch.append(extra)
                    except queue.Empty:
                        break

                if batch:
                    self._flush_batch_to_disk(batch)
                    batch.clear()

            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Unexpected error in flight recorder worker: {e}", exc_info=True)

        # Drain remaining on shutdown
        if batch:
            self._flush_batch_to_disk(batch)

    def _flush_batch_to_disk(self, events: list[DiagnosticEvent]) -> None:
        """Append batch of serialized events to JSONL journal with size rotation."""
        if not self._disk_available:
            return
        try:
            self._rotate_if_needed()
            with open(self.journal_path, "a", encoding="utf-8") as f:
                for evt in events:
                    f.write(evt.to_json() + "\n")
                f.flush()
        except Exception as e:
            logger.warning(f"Flight recorder disk write failed: {e}. Degrading to in-memory mode.")
            self._disk_available = False

    def _rotate_if_needed(self) -> None:
        """Check current journal file size and perform rotation if threshold exceeded."""
        if not self.journal_path.exists():
            return
        try:
            current_size = self.journal_path.stat().st_size
            if current_size < self.max_file_size_bytes:
                return

            # Perform rotation: flight_recorder.N.jsonl -> flight_recorder.N+1.jsonl
            for i in range(self.max_backup_files - 1, 0, -1):
                src = self.log_dir / f"flight_recorder.{i}.jsonl"
                dst = self.log_dir / f"flight_recorder.{i + 1}.jsonl"
                if src.exists():
                    if dst.exists():
                        try:
                            dst.unlink()
                        except OSError:
                            pass
                    try:
                        src.rename(dst)
                    except OSError:
                        pass

            backup_1 = self.log_dir / "flight_recorder.1.jsonl"
            if backup_1.exists():
                try:
                    backup_1.unlink()
                except OSError:
                    pass
            self.journal_path.rename(backup_1)

        except Exception as e:
            logger.warning(f"Flight recorder rotation error: {e}")

    def _recover_recent_from_disk(self) -> None:
        """Read trailing events from existing journal file into in-memory ring."""
        if not self.journal_path.exists():
            return
        try:
            lines: list[str] = []
            with open(self.journal_path, "r", encoding="utf-8", errors="replace") as f:
                # Read all lines or last lines
                for line in f:
                    line_str = line.strip()
                    if line_str:
                        lines.append(line_str)

            # Take up to in_memory_capacity trailing records
            recent_lines = lines[-self.in_memory_capacity :]
            for raw_line in recent_lines:
                try:
                    parsed = json.loads(raw_line)
                    evt = DiagnosticEvent.from_dict(parsed)
                    self._recent_events.append(evt)
                    dedup_key = f"{evt.fault_code}:{evt.source_type}:{evt.message}"
                    self._last_event_by_key[dedup_key] = (evt, time.monotonic())
                except Exception:
                    # Gracefully skip malformed or truncated lines
                    continue

        except Exception as e:
            logger.warning(f"Error recovering flight recorder history from {self.journal_path}: {e}")

    def shutdown(self, timeout_s: float = 2.0) -> None:
        """Flush queue and terminate background worker cleanly."""
        self._stop_event.set()
        if self._worker_thread and self._worker_thread.is_alive():
            try:
                self._write_queue.put_nowait(None)
                self._worker_thread.join(timeout=timeout_s)
            except Exception:
                pass


# Global singleton access
_GLOBAL_RECORDER: Optional[FlightRecorderJournal] = None
_GLOBAL_LOCK = threading.Lock()


def get_flight_recorder(log_dir: Optional[Path] = None) -> FlightRecorderJournal:
    """Get or initialize global FlightRecorderJournal instance."""
    global _GLOBAL_RECORDER
    with _GLOBAL_LOCK:
        if _GLOBAL_RECORDER is None:
            if log_dir is None:
                # Default fallback
                from ..desktop_server import get_default_user_data_dir
                log_dir = get_default_user_data_dir() / "logs"
            _GLOBAL_RECORDER = FlightRecorderJournal(log_dir=log_dir)
        return _GLOBAL_RECORDER
