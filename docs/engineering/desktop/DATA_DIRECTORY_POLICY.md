# AuscultaForge Data Directory & Storage Isolation Policy

- **Document Version:** 1.0.0
- **Scope:** Windows Storage Paths, Directory Hierarchy, Migration & Integrity Rules
- **Target Platform:** Windows 10/11 x64
- **Primary Code References:**
  - `software/pcg_app/desktop_server.py`
  - `software/pcg_app/app.py`
  - `software/frontend/src-tauri/src/process_manager.rs`
  - `software/frontend/src/api/bridgeClient.ts`

---

## 1. Core Principles

1. **Strict Decoupling of Binaries and State:**
   Installed binaries in `C:\Program Files\AuscultaForge` (or development directories) are strictly immutable and treated as read-only. The application never attempts to create files, logs, or sessions inside its installation root.
2. **Standard Windows User Profiles:**
   All persistent state resides in the standard Windows user application data directory:
   `%APPDATA%\AuscultaForge` (resolving typically to `C:\Users\<Username>\AppData\Roaming\AuscultaForge`).
3. **Unicode and Space Robustness:**
   Directory paths safely handle spaces, diacritics, and Unicode characters (e.g., `C:\Users\Ege Çağın Tepe\AppData\Roaming\AuscultaForge`).
4. **Data Preservation Across Upgrades:**
   Updating the desktop application or reinstalling preserves all historical recordings, manifests, and scientific reports.

---

## 2. Directory Hierarchy

```
%APPDATA%\AuscultaForge\
├── sessions\
│   └── <session_id>\
│       ├── raw.wav            (Logical mono 48 kHz Float32 PCM recording)
│       ├── session.json       (Telemetry metadata, sequence gaps, sample rate)
│       └── manifest.json      (Cryptographic SHA-256 hashes & integrity proofs)
├── analysis\
│   ├── assets\                (Uploaded reference signals & phantom stimuli)
│   ├── comparisons\           (H1 frequency response & reference-to-capture reports)
│   └── segmentation\          (Springer DBN/HMM S1/S2 acoustic boundary reports)
├── experiments\
│   ├── virtual-bench\         (Deterministic known-answer test run logs)
│   └── phantom\               (Hardware characterization trials)
├── logs\
│   ├── backend.log            (Rotated Python FastAPI / DSP server diagnostics)
│   └── desktop.log            (Tauri shell process supervision events)
└── backend_endpoint.json      (Runtime handshake metadata: port, PID, auth token)
```

---

## 3. Storage Verification & Cryptographic Integrity

Each session recorded in `sessions/<session_id>` is sealed upon finalization:
- `raw.wav` is flushed and closed.
- A cryptographic SHA-256 checksum is computed over the raw WAV file bytes.
- The checksum, sample count, duration, and hardware/virtual source metadata are committed into `session.json` and `manifest.json`.
- The verification endpoint `GET /api/sessions/<session_id>/verify` verifies:
  1. `sha256_match`: Live re-computation matches the stored SHA-256 hash.
  2. `sample_count_match`: Total audio frames match the header metadata.
  3. `sample_rate_match`: Stored WAV format matches logical acquisition rate.
  4. Detection of any corruption or unauthorized external modification.

---

## 4. Path Traversal & Safety Guarantees

All endpoints receiving `session_id`, `asset_id`, or `trial_id` enforce rigorous path sanitization:
- Rejection of path separators (`/`, `\`), null bytes, and traversal tokens (`..`).
- Canonicalization via `Path(storage_dir).resolve()` ensuring resolved file paths remain strictly inside the designated user storage directory.
