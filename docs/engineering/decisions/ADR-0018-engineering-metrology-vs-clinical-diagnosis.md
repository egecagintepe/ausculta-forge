# ADR-0018: Academic Scope — Technical Metrology vs. Clinical Diagnosis
**Status:** `ACCEPTED`  
**Date:** 2026-09-29  
**Deciders:** Academic Advisor Guidance, All Module Owners (Kaan, Ozan, Ege)  
**Technical Area:** Academic Scope, Ethics & Clinical Boundaries

## Context & Problem Statement
Undergraduate biomedical engineering projects frequently make unverified claims regarding medical disease detection (e.g. "our AI detects aortic stenosis and heart failure"). The course advisor for EEE495/EEE496 established a strict policy defining the boundary between engineering metrology and clinical medical diagnosis.

## Decision Drivers
* Academic rigor: Claims must be supported by empirical physical evidence. Clinical claims require certified medical device approvals, Institutional Review Board (IRB) ethics approval, and multi-center patient trials, which are outside the scope of an undergraduate senior design course.
* Course grading criteria: Grading is based on physical acoustic characterization, transducer comparison, embedded data-path integrity, and software engineering rigor—not medical pathology classification.

## Considered Alternatives
1. **Medical Diagnostic Device Claim:** Claiming the device diagnoses heart valve diseases.
   * *Critical Flaw:* Scientifically unsupportable; violates medical device regulations; causes immediate failure during capstone defense.
2. **Pure Academic Acoustic Prototype:** An engineering research instrument focused on **technical signal quality, acoustic transmission fidelity, frequency response, and repeatable measurement metrology** on acoustic bench phantoms.

## Decision
Formally established that AuscultaForge is an **Engineering Acoustic Metrology Prototype**:
* All physical characterization is performed on laboratory acoustic phantoms (audio exciter + silicone layer).
* The platform evaluates technical metrics: SNR, frequency response $H_1(f)$, coherence $\gamma^2(f)$, mains hum, latency, and sample continuity.
* Signal processing includes quality assessment (clipping, crest factor, noise levels) to assess signal usability, **not clinical pathology**.
* Machine learning segmentation (Springer LR-HSMM) is classified strictly as an advanced supporting research capability evaluated on open-access benchmark datasets.

## Consequences & Trade-Offs
* **Positive:** Unimpeachable academic defense; clear, achievable engineering goals; adherence to medical device ethics.
* **Negative:** The software explicitly disclaims medical utility and refuses to output clinical diagnostic labels.
