# Smart Digital Stethoscope — Desktop Client UI
## Module C (Computer Application & Quality Assessment)
Software Platform Codename: `AuscultaForge`

This directory contains the React / TypeScript / Vite local desktop frontend for the **Smart Digital Stethoscope** project.

---

## Capabilities
- **Live Dual-Trace Oscilloscope:** Real-time visualization of raw vs filtered PCG streams.
- **Spectrogram & Spectral Display:** Live frequency analysis and spectral frames.
- **Filter Controls:** Dynamic passband selection (e.g. recommended 20–200 Hz, bell, diaphragm).
- **Session Management:** Start/stop recording and session metadata inspection.
- **Device Health & Telemetry:** Connection status, stream continuity, and recording quality feedback.

---

## Run Locally

### Prerequisites
- Node.js 18+
- Active backend bridge server running at `http://127.0.0.1:8000`

### Steps
```bash
# 1. Install dependencies
npm install

# 2. Run local development server
npm run dev
```

The frontend will be available at `http://localhost:3000`.
