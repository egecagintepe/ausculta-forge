# Data Directory

This directory stores datasets, audio recordings, and benchmark data for the AuscultaForge project.

## Policy: No Medical or Audio Data in Git

**Do not commit raw audio files, clinical recordings, or medical datasets to Git.**
All binary dataset files (`.wav`, `.dat`, `.hea`, `.mat`, `.zip`, `.tar.gz`, etc.) under `data/raw/` and `data/processed/` are explicitly ignored by `.gitignore`.

## Recommended Directory Structure

```text
data/
├── raw/               # Pristine, unmodified downloaded datasets
│   └── .gitkeep
├── processed/         # Cleaned, standardized, or resampled records
│   └── .gitkeep
└── README.md          # Documentation and acquisition guidelines
```

## Future Data Sources

When validating the DSP pipeline and heart sound segmentation offline, use benchmark open-access PCG datasets:

1. **PhysioNet / Computing in Cardiology (CinC) Challenge 2016**
   - *Title:* Classification of Normal/Abnormal Heart Sound Recordings
   - *Description:* Phonocardiogram recordings collected from several medical centers, sampled at 2,000 Hz or 4,000 Hz.
   - *Link:* [PhysioNet CinC Challenge 2016](https://physionet.org/content/challenge-2016/1.0.0/)

2. **CirCor DigiScope Phonocardiogram Dataset (PhysioNet)**
   - *Title:* The CirCor DigiScope Dataset of Pediatric Heart Sound Recordings
   - *Description:* Open-access pediatric PCG records collected from 4 auscultation locations (Aortic, Pulmonic, Tricuspid, Mitral) at 4,000 Hz.
   - *Link:* [CirCor DigiScope on PhysioNet](https://physionet.org/content/circor-digiscope/1.0.3/)

3. **In-house Test Recordings**
   - Acquired using the prototype stethoscope (Ozan) and MCU digital stream (Kaan).
   - Place in-house exploratory samples locally in `data/raw/prototype_recordings/` for DSP testing without tracking them in Git.

## Usage in Software

To load a downloaded mono `.wav` file into the PCG software pipeline, utilize `WavSource`:

```python
from pathlib import Path
from pcg_core.sources import WavSource
from pcg_core.dsp import StreamingBandpass

source = WavSource(Path("data/raw/sample_heart_sound.wav"), block_size=256)
dsp = StreamingBandpass(sample_rate_hz=4000)

for block in source.blocks():
    filtered_block = dsp.process(block)
    # downstream metrics or storage
```
