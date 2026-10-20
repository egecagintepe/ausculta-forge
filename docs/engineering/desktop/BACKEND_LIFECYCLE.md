# AuscultaForge Backend Subprocess Lifecycle & Process Supervision

- **Document Version:** 1.0.0
- **Scope:** Process Lifecycle, Port Allocation, Handshake, Supervision & Recovery
- **Target Platform:** Windows 10/11 x64
- **Primary Code References:**
  - `software/pcg_app/desktop_server.py`
  - `software/frontend/src-tauri/src/process_manager.rs`
  - `software/frontend/src-tauri/src/lib.rs`

---

## 1. Lifecycle State Machine

The AuscultaForge desktop backend follows a strict finite-state machine from application launch through termination:

```
[INIT] ──> [DISCOVERY] ──> [SPAWN] ──> [JOB_BIND] ──> [HANDSHAKE] ──> [ACTIVE_SUPERVISED]
                                                                           │
                                                                           ├──> [RESTART_REQUESTED] ──> [STOP] ──> [SPAWN]
                                                                           │
                                                                           └──> [SHUTDOWN] ──> [CLEANUP] ──> [TERMINATED]
```

### Detailed State Transitions

1. **DISCOVERY:**
   The Tauri host inspects potential backend executable locations in priority order:
   - Packaged installation path: `<exe_dir>/auscultaforge-backend/auscultaforge-backend.exe`
   - Tauri bundle resources: `<exe_dir>/resources/auscultaforge-backend/auscultaforge-backend.exe`
   - Workspace build output: `software/dist_backend/auscultaforge-backend/auscultaforge-backend.exe`
   - Development virtual environment: `.venv/Scripts/python.exe -m pcg_app.desktop_server`
   - System Python: `python.exe -m pcg_app.desktop_server`

2. **SPAWN:**
   The process is launched with command-line arguments:
   - `--port 0` (binds to ephemeral port)
   - `--parent-pid <tauri_pid>` (passes parent PID for watchdog monitoring)
   - `CREATE_NO_WINDOW` flag (`0x08000000`) prevents a flashing Windows console command prompt.
   - Piped `stdout` and `stderr` handles.

3. **JOB_BIND (Kernel Supervision):**
   Prior to reading input, the child process handle is enrolled into a Win32 Job Object configured with `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`.
   This ensures that even if the host application crashes or is killed by Task Manager, the Windows kernel terminates the backend tree.

4. **HANDSHAKE:**
   The backend binds to an ephemeral loopback socket on `127.0.0.1:0`.
   Once bound and healthy, it commits endpoint metadata to disk and emits a single atomic line on stdout:
   ```
   AUSCULTAFORGE_BACKEND_READY:{"port":58903,"auth_token":"8a3c...","pid":12344,"storage_dir":"C:\\Users\\...\\AppData\\Roaming\\AuscultaForge","status":"healthy"}
   ```
   The Tauri host parses this JSON line (with a 20-second timeout) and populates the `BackendConfig` state.

5. **ACTIVE_SUPERVISED:**
   The backend continuously serves REST and WebSocket requests while the watchdog thread monitors the parent PID.

6. **SHUTDOWN / CLEANUP:**
   When the Tauri window closes, Tauri's `RunEvent::Exit` fires, calling `backend_manager.stop()`.
   `stop()` sends a kill signal, waits for exit, and closes the Job Object handle.
