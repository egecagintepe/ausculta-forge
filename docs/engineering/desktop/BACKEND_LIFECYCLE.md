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
   The Tauri host inspects backend executable locations based on build mode:
   - **Production Release Mode (`#[cfg(not(debug_assertions))]`):**
     1. Tauri resource directory: `<resource_dir>/auscultaforge-backend/auscultaforge-backend.exe`
     2. Relative to executable: `<exe_dir>/auscultaforge-backend/auscultaforge-backend.exe`
     3. *Strict Packaging Boundary:* Production builds refuse silent fallback to global or system Python. If the bundled backend is missing, startup fails fast with a clear diagnostic.
   - **Development Mode (`#[cfg(debug_assertions)]`):**
     1. Workspace PyInstaller output: `software/dist_backend/auscultaforge-backend/auscultaforge-backend.exe`
     2. Virtual environment: `.venv/Scripts/python.exe software/pcg_app/desktop_server.py`
     3. Global Python: `python software/pcg_app/desktop_server.py`

2. **SPAWN:**
   The process is launched with command-line arguments:
   - `--port 0` (binds to an OS-allocated dynamic ephemeral port)
   - `--parent-pid <tauri_pid>` (passes parent PID for watchdog monitoring)
   - `CREATE_NO_WINDOW` flag (`0x08000000`) prevents a flashing Windows console command prompt.
   - Piped `stdout` and `stderr` handles.

3. **JOB_BIND (Kernel Supervision):**
   Prior to reading input, the child process handle is enrolled into a Win32 Job Object configured with `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`.
   This ensures that when supported by OS permissions, closing the host application or terminating it via Task Manager causes the Windows kernel to terminate child processes. If Job Object creation or assignment is restricted by host environment policies, a warning is logged and the watchdog thread serves as the application-level safeguard.

4. **NON-BLOCKING HANDSHAKE & HEALTH CHECK:**
   - The backend binds to an ephemeral loopback socket on `127.0.0.1:0`.
   - It outputs an atomic handshake line on stdout adhering to contract `1.0.0`:
     ```
     AUSCULTAFORGE_BACKEND_READY:{"schema_version":"1.0.0","app":"AuscultaForge Desktop","version":"0.1.0-alpha.1","status":"ready","host":"127.0.0.1","port":58903,"auth_token":"8a3c...","pid":12344,"storage_dir":"C:\\Users\\...\\AppData\\Roaming\\AuscultaForge","user_data_dir":"C:\\Users\\...\\AppData\\Roaming\\AuscultaForge",...}
     ```
   - The Tauri host reads stdout via a background thread feeding an `mpsc::channel` with a bounded 20-second timeout, draining `stderr` concurrently to prevent pipe buffer deadlocks.
   - Child process crashes are detected immediately via `try_wait()`, reaping the process handle without deadlocking.
   - After parsing the handshake JSON, Tauri issues an active HTTP `GET /api/health` request with the `X-AuscultaForge-Auth` header. Only upon receiving `200 OK` is the backend declared operational.

5. **ACTIVE_SUPERVISED:**
   The backend continuously serves REST and WebSocket requests while the parent-PID watchdog monitors the Tauri process.

6. **SHUTDOWN / CLEANUP:**
   When the Tauri window closes, Tauri's `RunEvent::Exit` fires, calling `backend_manager.stop()`.
   `stop()` terminates the child process, drains pipes, reaps process handles, and closes the Job Object handle.
