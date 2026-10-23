# Morning baseline audit — 2026-10-23

Starting local and remote main: `6aadccfcc5f4c401bdf18638ea343d705a41c0d1`.
One worktree, main, clean. Predecessor files and six First Contact commits exist.
No concurrent work was present. No board has been identified or opened.

## Evidence checked before editing

Firmware: CMake, sdkconfig.defaults, genuine dependencies.lock, g1/acquisition
portable core, TinyUSB owner, default-off I2S adapter, Kconfig, host C bridge,
frozen golden vectors. First Contact: hardware_workflow.py, bringup.py,
preflight.py/PowerShell, shared acceptance.py, engine, DeviceView, board dossier,
electrical and lab runbooks, and first_contact evidence exist. Preserved G1 and
I2S compile products exist locally; their manifests are historical build evidence,
not proof of boot. The current shell has no exported IDF; pinned local SDK exists
under ignored firmware/build. No initial compilation/test failure is inferred
from that shell state. New executions are recorded in MORNING_RELEASE_REPORT.md.

Implemented: real binary USB engine, nonce/configuration checks, exact deterministic
G1 policy, evidence export, default-off DMA I2S, full-rate raw float32 recording,
stateful DSP, diagnostics and optional frozen-model research. Simulated: loopback
device/virtual bench, software fault injection and host-compiled C firmware.
Physical G0–G3/H0–H5: NOT_EXECUTED. No clinical or acoustic validation exists.

## Findings and disposition

| Severity | Starting defect / gap | Required correction |
| --- | --- | --- |
| P1 | pyserial missing from reproducible Python install metadata; PyWavelets missing from package dependencies | Declare runtime requirements; test clean install |
| P1 | USB worker touches asyncio client queue from another thread | Bounded delivery on owning event loop; thread regression |
| P1 | Raw record happens after DSP, so DSP exceptions can discard acquisition evidence | Record before processing; failure regression |
| P1 | Simulated USB recordings carry hardware acquisition provenance | Explicit software_simulated mode, no physical device metadata |
| P1 | Normal USB STOP leaves recording open; repeated sessions can append to previous recording | Finalize recording, reset DSP/session state before next START |
| P1 | Transport open failure after Serial construction can retain handle | Close partially initialized serial handle |
| P1 | Unexpected worker/callback exception bypasses teardown | Guaranteed finally cleanup and future settlement |
| P1 | Committed PyInstaller spec contains workstation absolute paths; dynamic USB imports need bundle verification | Relative spec and serial hidden imports; actual packaged smoke |
| P2 | CLI lacks doctor alias, boot capture and passive re-enumeration watch | Extend existing CLI with bounded, explicit commands |
| P2 | Requested Turkish morning guide, laptop setup, pin/checklist split and acceptance matrix absent | Add focused operational documents |

No demonstrated software P0 at baseline. Physical connector routing, N16R8 marking,
power isolation and microphone pinout are blocking manual gates for hardware writes
or wiring. Passive enumeration cannot settle port ownership; access failures must
be reported on deliberate selected-port open, without probing unrelated ports.

Scope reaches CLI callers/tests/docs, runtime package metadata/bundler, session
worker callbacks, StreamManager recording/display, API STOP/start and their tests.
Original recordings, trained weights, frozen research metrics and protocol bytes
must remain intact. No branch/worktree, flash, driver install or eFuse operation.
