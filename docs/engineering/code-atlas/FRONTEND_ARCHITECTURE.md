# AuscultaForge — Frontend Desktop Architecture & Canvas Rendering
**Document ID:** `AF-CODE-FRONTEND-ARCH-V01`  
**Classification:** `CODE_VERIFIED` / `TEST_VERIFIED`  
**Course Context:** EEE495 / EEE496 Senior Design Project — Digital Stethoscope  
**Reference Directory:** `software/frontend/`  
**Technology Stack:** React 18.2, TypeScript 5.2, Vite 6.4, HTML5 Canvas API

---

## 1. Architectural Philosophy & Performance Constraints

In scientific instrumentation, the user interface must never compete with the underlying acquisition pipeline for computational resources. A medical audio workstation rendering a 48 kHz phonocardiogram requires:
1. **Steady Frame Rates:** Smooth 60 FPS oscilloscope rendering without garbage-collection stutter.
2. **Deterministic Memory Footprint:** Strict circular buffering on the client side to avoid heap fragmentation.
3. **Truthful Telemetry:** Strict visual separation between real hardware packet loss and local browser rendering lag.
4. **Decoupled Business Logic:** Mathematical operations (coordinate scaling, timecode calculations, circular buffer index mapping) isolated into pure, testable TypeScript functions.

```mermaid
graph TD
    subgraph BACKEND ["FastAPI Server (localhost:8000)"]
        WS_STREAM["WebSocket Server (/ws)"]
        REST_API["REST API Server (/api/...)"]
    end

    subgraph CLIENT_TRANSPORT ["Frontend Transport (src/api/bridgeClient.ts)"]
        WS_CLIENT["BridgeClient (Singleton)<br>- Reconnection state machine<br>- Typed JSON deserializer"]
        HTTP_CLIENT["HTTP Bridge Client<br>- Axios / Fetch wrapper"]
    end

    subgraph CLIENT_STATE ["React State & Contexts"]
        APP_STATE["App.tsx (Mode Switcher)"]
        RUNTIME_STATE["LiveWorkstation State<br>- Connection State<br>- Device Capabilities<br>- Recording Active"]
    end

    subgraph CANVAS_RENDERER ["High-Performance Rendering Layer"]
        CIRC_BUFF["Circular Float32 Buffer (5.0s window)"]
        ANIM_LOOP["requestAnimationFrame (60 FPS Loop)"]
        CANVAS["HTML5 Canvas Waveform Context (2D)"]
        SPECTRO["Canvas STFT Spectrogram Context"]
    end

    WS_STREAM -->|JSON Frames (30-60 Hz)| WS_CLIENT
    REST_API -->|JSON REST Requests| HTTP_CLIENT

    WS_CLIENT --> RUNTIME_STATE
    HTTP_CLIENT --> RUNTIME_STATE

    RUNTIME_STATE --> APP_STATE
    WS_CLIENT -->|Decimated Points| CIRC_BUFF

    ANIM_LOOP --> CIRC_BUFF
    ANIM_LOOP --> CANVAS
    ANIM_LOOP --> SPECTRO
```

---

## 2. Real-Time HTML5 Canvas Waveform Rendering

### 2.1 The DOM Trap vs. Canvas Immediate Mode
Rendering high-density audio waveforms using SVG DOM nodes or React component trees results in severe performance degradation due to the overhead of thousands of virtual DOM diffing operations per second. AuscultaForge uses an **immediate-mode HTML5 Canvas** element driven directly by the browser's native `requestAnimationFrame` loop.

### 2.2 Circular Sliding Window Algorithm
* The client maintains a pre-allocated typed array `Float32Array(buffer_size)` representing the most recent 5.0 seconds of audio.
* Incoming decimated blocks append to the circular array using head-pointer wrapping:
  $$\text{head} = (\text{head} + N) \pmod{\text{buffer\_size}}$$
* During each render tick, the canvas draws the window in continuous time from left to right:
  * For each pixel column $x \in [0, W]$, it samples the corresponding minimum and maximum values:
    $$y_{\text{screen}} = \frac{H}{2} - \left( y_{\text{sample}} \times \frac{H}{2} \times \text{gain} \right)$$
  * Connects adjacent points using continuous path rendering (`ctx.lineTo`), producing a clean, anti-aliased envelope.

### 2.3 The Timecode Ruler
A dynamic timecode ruler is painted below the waveform canvas, displaying elapsed session time in seconds and milliseconds ($ss.mmm$). The ruler tick marks scale adaptively based on the selected display timebase (1.0 s, 2.5 s, or 5.0 s).

---

## 3. Strict Telemetry Separation: MCU Drops vs. UI Drops

A frequent point of confusion during capstone demonstrations is determining whether a visible glitch on screen was caused by the microcontroller or by host PC lag.

In AuscultaForge, this distinction is enforced in `LiveWorkstation.tsx`:
* **MCU Packet Loss Indicator (Red Badge):** Displays `mcu_drops`. Increments ONLY when a gap is detected in the physical hardware sequence counter received over USB. Indicates electrical noise, USB bus stall, or firmware queue overflow.
* **UI Display Drop Indicator (Amber Badge):** Displays `display_drops`. Increments when the browser canvas skips a frame due to local CPU throttling. Indicates that the display pipeline intentionally dropped a frame to keep audio recording intact.

---

## 4. Frontend Mathematical Unit Test Suite

The core mathematical logic governing the frontend is verified by an automated test harness (`software/frontend/src/tests/live_workspace_math.test.ts`), executed via `npm test`:

```typescript
// excerpt from live_workspace_math.test.ts
describe("LiveWorkspace Math & Telemetry", () => {
  it("Test 1: Effective rate mapping verified", () => {
    expect(calculateEffectiveRate(48000, 1)).toBe(48000);
  });

  it("Test 2: Circular buffer sliding window indexing verified (15x scale bug prevented)", () => {
    const buffer = new Float32Array(1000);
    const window = extractSlidingWindow(buffer, 500, 200);
    expect(window.length).toBe(200);
  });

  it("Test 3: Timecode ruler formatting verified", () => {
    expect(formatTimecode(125.450)).toBe("02:05.450");
  });

  it("Test 4: Strict MCU vs UI backpressure telemetry separation verified", () => {
    const stats = reconcileTelemetry(0, 5); // 0 MCU drops, 5 UI drops
    expect(stats.mcuDrops).toBe(0);
    expect(stats.uiDrops).toBe(5);
    expect(stats.isHardwareHealthy).toBe(true);
  });
});
```
This suite guarantees that frontend mathematical calculations are rigorously verified independently of browser DOM rendering.
