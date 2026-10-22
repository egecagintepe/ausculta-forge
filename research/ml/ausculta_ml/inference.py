"""Versioned, local CPU, research-only inference interface for future desktop integration."""
from pathlib import Path
import json
import numpy as np
import torch
from .data import make_spectrogram


def predict_recordings(model_dir: Path, paths: list[str]) -> dict:
    model_dir=Path(model_dir)
    meta=json.loads((model_dir/'manifest.json').read_text(encoding='utf8'))
    if not paths or len(paths)>64:raise ValueError('Pass 1..64 PCG WAV paths')
    specs=[]
    frame_len=round(meta['crop_seconds']*meta['sample_rate']/meta['stft_hop'])
    for p in paths[:meta['max_recordings']]:
        s=make_spectrogram(p,sample_rate=meta['sample_rate'],nfft=meta['stft_n_fft'],
              hop=meta['stft_hop'],low_hz=meta['band_low_hz'],high_hz=meta['band_high_hz']).astype('float32')
        specs.append(s)
    model=torch.jit.load(str(model_dir/'murmur_mil_cpu.pt'),map_location='cpu').eval()
    # Match held-out inference protocol: 3 deterministic temporal windows per location.
    logits=[]
    with torch.no_grad():
        for offset in (0., .5, 1.):
            tensor=torch.zeros((1,meta['max_recordings'],1,specs[0].shape[0],frame_len),dtype=torch.float32)
            mask=torch.zeros((1,meta['max_recordings']),dtype=torch.bool)
            for i,s in enumerate(specs):
                if s.shape[0]!=specs[0].shape[0]:raise ValueError('Mismatched spectrogram frequency bins')
                left=int((s.shape[1]-frame_len)*offset) if s.shape[1]>frame_len else 0
                cropped=s[:,left:left+frame_len]
                tensor[0,i,0,:,:cropped.shape[1]]=torch.from_numpy(cropped)
                mask[0,i]=True
            logits.append(model(tensor,mask).float()[0])
        p=float(torch.sigmoid(torch.stack(logits).mean()))
    return {'research_only':True,'task':'patient_level_murmur_present_vs_absent',
            'positive_probability':p,'validation_selected_threshold':meta['threshold'],
            'predicted_label':('research_pattern_present' if p>=meta['threshold'] else 'research_pattern_absent'),
            'model_version':meta['model_version'],
            'warning':'Not a medical diagnosis; domain-shifted hardware recordings require external validation.'}
