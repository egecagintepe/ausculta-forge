# AuscultaForge Desktop Security Model & Local Bridge Protection

- **Document Version:** 1.0.0
- **Scope:** Threat Analysis, Loopback Protection, Per-Process Authentication & CSP
- **Target Platform:** Windows 10/11 x64
- **Primary Code References:**
  - `software/pcg_app/app.py`
  - `software/pcg_app/desktop_server.py`
  - `software/frontend/src/api/bridgeClient.ts`
  - `software/frontend/src-tauri/tauri.conf.json`
  - `software/tests/test_desktop_security.py`

---

## 1. Threat Analysis for Desktop-Local Web Applications

Traditional web applications running a local backend on a fixed port (such as `http://127.0.0.1:8000`) suffer from critical security vulnerabilities:
1. **Drive-By Browser Requests (Cross-Origin Execution):** An external website visited by the user in Google Chrome or Microsoft Edge could issue background `fetch('http://127.0.0.1:8000/api/sessions/...')` or connect to `ws://127.0.0.1:8000/ws`, deleting recordings, initiating simulated hardware states, or exfiltrating medical specimen data.
2. **Fixed Port Sniffing & Collisions:** A developer running multiple instances or unrelated services on port 8000 causes port binding crashes or hijacking.
3. **Privilege Escalation & Command Injection:** Desktop shells exposing arbitrary shell execution APIs to the frontend enable remote code execution if malicious assets are loaded.

---

## 2. Desktop Security Architecture

AuscultaForge Desktop enforces a multi-layer local defense-in-depth model:

### Layer 1: Strict Loopback Interface Binding
The backend server binds strictly to the loopback interface (`127.0.0.1`), never to wildcard addresses (`0.0.0.0`). Network interfaces (Ethernet, Wi-Fi) cannot reach the backend port.

### Layer 2: Ephemeral Dynamic Port Allocation
The backend binds to OS port 0, requesting an ephemeral port from the Windows TCP stack (typically in the 49152–65535 range). The port is non-deterministic and unknown to external processes.

### Layer 3: Per-Instance Cryptographic Authentication Token
Upon startup, `desktop_server.py` generates a 256-bit cryptographically secure token:
```python
auth_token = secrets.token_hex(32)
```
- **REST Endpoints:** The frontend attaches this token via the custom header `X-AuscultaForge-Auth: <token>`.
- **WebSocket Upgrade:** The frontend attaches the token as a query parameter `ws://127.0.0.1:<port>/ws?token=<token>`.
- **File Export Endpoints:** Direct download links attach `?token=<token>`.
- **Rejection Policy:** Any unauthenticated or mismatched request is immediately rejected with HTTP `401 Unauthorized` or WebSocket close code `1008 (Policy Violation)`.
- **Backward Compatibility:** When launched without an authentication token (such as in legacy pytest fixtures or direct `python -m pcg_app.server`), authentication is automatically disabled.

### Layer 4: Content Security Policy (CSP)
The WebView2 container enforces a locked-down CSP defined in `tauri.conf.json`:
```
default-src 'self' http://127.0.0.1:* ws://127.0.0.1:*;
script-src 'self' 'unsafe-inline';
style-src 'self' 'unsafe-inline' https://fonts.googleapis.com;
font-src 'self' https://fonts.gstatic.com;
img-src 'self' data: blob:;
```
External scripts and unauthorized network origins are blocked by the browser engine.

### Layer 5: Path Traversal Defenses
Session IDs, asset IDs, and file export paths are strictly sanitized using regex and path canonicalization. Any parameter containing `..`, `/`, `\`, or absolute drive specifiers is rejected.
