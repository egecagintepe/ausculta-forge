# AuscultaForge — Agent & Developer Instructions (25 Nov 2026)

## Handover & Current State
- **Active Branch:** `feature/rev04-evidence-integration` (PR #36).
- **Target Session:** 25 November 2026 Physical Laboratory Session.
- **Master Quickstart Guide:** [`START_HERE_2026-11-25.md`](START_HERE_2026-11-25.md) (or [`docs/engineering/hardware/START_HERE_2026-11-25.md`](docs/engineering/hardware/START_HERE_2026-11-25.md)).
- **Laptop Single-Prompt Execution:** [`LAPTOP_PROMPT.md`](LAPTOP_PROMPT.md).
- **Operator Run Sheet (TR):** [`docs/engineering/hardware/LAB_RUN_SHEET_2026-11-25.md`](docs/engineering/hardware/LAB_RUN_SHEET_2026-11-25.md).

## Operational Rules for Agents
1. **Never Bypass Physical Acceptance:** Live physical experiment passes require real physical recordings, hardware USB CDC discovery, quiet baseline verification, and operator attestations. Never fabricate physical test passes.
2. **Deterministic Simulation:** When hardware is not connected, use `.\tools\hardware\run_lab_phantom_workflow.ps1 -Simulate` or `run_phantom_pcg_experiment.py --simulate`.
3. **Environment Setup:** Run `.\tools\hardware\run_lab_phantom_workflow.ps1 -SetupOnly` to verify Python modules, unit test suite (35/35 passing), and reference PCG hash without triggering hardware capture or audio playback.
4. **Git Discipline:** Work on `feature/rev04-evidence-integration`. Do NOT merge directly into `main` or force-push.
