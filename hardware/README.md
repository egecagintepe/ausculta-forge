# Hardware Directory
## Smart Digital Stethoscope: Heart Sound Acquisition, Signal Processing and Quality Assessment
### EEE495 / EEE496 Senior Design Project â€” Modules A & B
Software / Platform Codename: `AuscultaForge`

This directory hosts hardware designs, mechanical specifications, analogue front-end schematics, component evaluations, and acoustic phantom modeling.

---

## Responsibilities & Module Ownership

### Module A â€” Acquisition Hardware & Characterisation (Owner: Kaan)
- Transducer evaluation: electret condenser vs MEMS microphones.
- Acoustic chestpiece coupling and mechanical positioning.
- Analogue front-end pre-amplification and signal conditioning.
- Acoustic phantom physical system: test chamber, exciter/speaker setup, and compliant silicone/gel tissue layer.
- Repeatable phantom measurement protocols and physical characterisation.

### Module B â€” Embedded Acquisition & Hardware Integration (Owner: Ozan)
- Component selection and Turkish sourcing (BOM v0.1 / v1.0).
- Microcontroller development board integration (ESP32-S3 exposing Native USB).
- Power regulation and supply decoupling.
- Interfacing wiring, breadboard prototyping, and soldered prototype assembly.

---

## Prototyping Strategy & Policy
- **Breadboard Development:** Initial sensor evaluation and signal conditioning are developed on solderless breadboards and dev-boards.
- **Soldered Prototype:** A soldered prototype (perfboard / stripboard) is entirely sufficient for course completion unless experimental bench measurements formally justify a custom PCB spin. Custom PCB fabrication remains optional.
