# ADR-0002: Physical Transport — Wired Native USB vs. Wireless
**Status:** `ACCEPTED`  
**Date:** 2026-09-26  
**Deciders:** Module B (Ozan), Module C (Ege), Academic Advisor Guidance  
**Technical Area:** System Architecture & Data Transport

## Context & Problem Statement
A digital stethoscope prototype must transport digitized cardiac phonocardiography signals ($48,000 \text{ Hz}, 32\text{-bit}$ containers, $\approx 1.536 \text{ Mbps}$) to a host PC for real-time visualization and scientific analysis. The team evaluated whether to use wireless protocols (Bluetooth / Wi-Fi) or a wired USB connection.

## Decision Drivers
* Strict sample continuity requirement: $0.0\%$ dropped samples over a 30-minute continuous streaming session.
* Low and deterministic propagation latency ($\le 50 \text{ ms}$).
* Immunity to 2.4 GHz electromagnetic interference in dense laboratory environments.
* Minimal microcontroller power dissipation and thermal drift.

## Considered Alternatives
1. **Bluetooth Classic (SPP) / BLE Audio:**
   * High RF packet loss rate in university lab environments.
   * Variable latency and packet buffering jitter ($> 100 \text{ ms}$).
   * Limited sustained throughput under non-ideal link margins.
2. **Wi-Fi (TCP / UDP Sockets):**
   * High active power consumption ($> 250 \text{ mA}$), causing thermal rise in the chestpiece.
   * Connection drops, DHCP delays, and complex network setup during academic grading sessions.
3. **Wired Native USB 2.0 (CDC-ACM):**
   * Direct differential signaling over shielded twisted-pair copper cable.
   * Sustained bandwidth $\approx 12 \text{ Mbps}$, offering $> 80\%$ headroom over audio payload.
   * Zero RF interference, zero pairing steps, zero dropped packets under normal operating conditions.

## Decision
Selected **Wired Native USB** as the primary physical transport:
* Power delivery ($5\text{ V}$ VBUS) and data transfer are unified into a single cable.
* Ensures reproducible, jitter-free laboratory metrology for the six mandatory advisor measurements.

## Consequences & Trade-Offs
* **Positive:** Guaranteed bit-exact transmission; zero battery management overhead for initial prototype.
* **Negative:** Stethoscope prototype is tethered to the host PC via a USB cable. (Wireless mobility is deferred to optional future revisions).
