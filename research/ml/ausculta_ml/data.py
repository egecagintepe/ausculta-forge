"""CirCor v1.0.3 corpus indexing, leakage-safe grouped splitting and spectrogram cache."""
from __future__ import annotations
import hashlib
import json
import random
from pathlib import Path
from functools import lru_cache
import numpy as np
import pandas as pd
import soundfile as sf
from scipy.signal import resample_poly, stft
from sklearn.model_selection import train_test_split
from math import gcd

MURMUR = {'Present': 1, 'Absent': 0}
LOCATIONS = ('AV', 'PV', 'TV', 'MV', 'Phc')


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def make_index(root: Path, index_path: Path) -> list[dict]:
    """Index explicit subject labels; do NOT mistake a patient-level murmur label for local ground truth."""
    root = Path(root)
    meta = root / 'training_data.csv'
    if not meta.is_file():
        raise FileNotFoundError(f'CirCor training_data.csv missing: {meta}. Download complete PhysioNet v1.0.3 dataset.')
    df = pd.read_csv(meta)
    needed = {'Patient ID', 'Murmur', 'Recording locations:', 'Additional ID'}
    if not needed.issubset(df.columns):
        raise ValueError(f'Missing columns: {needed - set(df.columns)}')
    wav_dir = root / 'training_data'
    if not wav_dir.is_dir():
        raise FileNotFoundError(f'CirCor WAV folder missing: {wav_dir}')
    out = []
    for _, row in df.iterrows():
        label = str(row['Murmur']).strip()
        if label not in MURMUR:  # Unknown is NOT a negative sample.
            continue
        sid = str(int(row['Patient ID']))
        recs = []
        for loc in LOCATIONS:
            # Handles versions with suffix like 50782_MV_1.wav; deterministic sorted order.
            recs += sorted(wav_dir.glob(f'{sid}_{loc}.wav'))
            recs += sorted(wav_dir.glob(f'{sid}_{loc}_*.wav'))
        recs = sorted(set(recs))
        if not recs:
            raise FileNotFoundError(f'No WAV for patient {sid}; dataset incomplete')
        other = row['Additional ID']
        alt = str(int(float(other))) if pd.notna(other) and str(other).strip() not in ('', 'nan') else None
        out.append({'patient_id': sid, 'additional_id': alt, 'label': MURMUR[label],
                    'paths': [str(x.resolve()) for x in recs], 'source': 'CirCor 1.0.3',
                    'label_level': 'patient', 'murmur': label})
    if not out:
        raise ValueError('No Present/Absent patients in CirCor CSV')
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(json.dumps({'dataset_version': '1.0.3', 'csv_sha256': sha256_file(meta),
                                      'patients': out}, indent=2), encoding='utf-8')
    return out


def _groups(records: list[dict]) -> dict[str, str]:
    # Union-find: one person could appear in multiple campaigns under alternate IDs.
    parent = {}
    def root(x):
        parent.setdefault(x, x)
        if parent[x] != x:
            parent[x] = root(parent[x])
        return parent[x]
    def union(a,b):
        ra, rb = root(a), root(b)
        parent[ra] = rb
    for p in records:
        root(p['patient_id'])
        if p.get('additional_id'):
            union(p['patient_id'], p['additional_id'])
    return {p['patient_id']: root(p['patient_id']) for p in records}


def frozen_split(records: list[dict], manifest: Path, seed=42, val_fraction=.15, test_fraction=.15):
    """Freeze patient-group IDs once; no retuning splits after observing test metrics."""
    manifest = Path(manifest)
    groupmap = _groups(records)
    groups: dict[str, list[dict]] = {}
    for p in records:
        groups.setdefault(groupmap[p['patient_id']], []).append(p)
    if manifest.is_file():
        payload = json.loads(manifest.read_text())
        sets = payload['splits']
        indexed = {r['patient_id'] for r in records}
        if set(sum(sets.values(), [])) != indexed:
            raise ValueError('Frozen split no longer matches current dataset. Refusing silent regeneration.')
    else:
        keys = sorted(groups)
        labels = [max(int(p['label']) for p in groups[k]) for k in keys]  # grouping only
        testn = test_fraction
        trainval, test = train_test_split(keys, test_size=testn, random_state=seed, stratify=labels)
        labels_tv = [max(int(p['label']) for p in groups[k]) for k in trainval]
        train, val = train_test_split(trainval, test_size=val_fraction/(1-testn),
                                     random_state=seed+1, stratify=labels_tv)
        sets = {k: sorted([p['patient_id'] for g in gs for p in groups[g]])
                for k, gs in [('train', train), ('val', val), ('test', test)]}
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(json.dumps({'seed': seed, 'dataset': 'CirCor v1.0.3 public training subset',
            'unit': 'linked patient IDs; additional_id grouped',
            'splits': sets}, indent=2), encoding='utf-8')
    ownership = {}
    for partition, ids in sets.items():
        for sid in ids:
            g = groupmap[sid]
            if g in ownership and ownership[g] != partition:
                raise AssertionError(f'Data leakage! Cross-campaign patient group in {ownership[g]} and {partition}')
            ownership[g] = partition
    byid = {p['patient_id']: p for p in records}
    return {key: [byid[sid] for sid in ids] for key, ids in sets.items()}


def make_spectrogram(path: str, sample_rate=2000, nfft=512, hop=128, low_hz=15, high_hz=650):
    x, sr = sf.read(path, dtype='float32', always_2d=True)
    x = np.mean(x, axis=1).astype(np.float32)
    if sr != sample_rate:
        den = gcd(int(sr), int(sample_rate))
        x = resample_poly(x, sample_rate // den, int(sr) // den).astype('float32')
    if not np.all(np.isfinite(x)) or len(x) < nfft:
        raise ValueError(f'Invalid / too-short PCG waveform {path}')
    x = x - np.mean(x)
    frequencies, times, z = stft(x, fs=sample_rate, nperseg=nfft, noverlap=nfft-hop,
                                  boundary=None, padded=False)
    mask = (frequencies >= low_hz) & (frequencies <= high_hz)
    power = np.abs(z[mask, :]) ** 2
    db = 10 * np.log10(np.maximum(power, 1e-12))
    # Relative dynamic range, no absolute dB SPL calibration claim.
    peak = float(np.max(db))
    relative = np.clip(db-peak, -80.0, 0.0) / 40.0 + 1.0
    return relative.astype('float16')


def prepare_spectrogram_cache(records: list[dict], cache_dir: Path, **params):
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    paths = sorted(set(p for record in records for p in record['paths']))
    for i, p in enumerate(paths):
        output = cache_dir / (Path(p).stem + '.npz')
        if output.exists():
            continue
        arr = make_spectrogram(p, **params)
        np.savez_compressed(output, spec=arr)
        if (i+1) % 250 == 0:
            print(f'Cached {i+1}/{len(paths)} recordings')
    print(f'Cache complete: {len(paths)} recordings at {cache_dir}')


@lru_cache(maxsize=256)
def _read_cached(cache_path: str):
    with np.load(cache_path) as f:
        return f['spec'].astype('float32')


class PatientSpectrogramDataset:
    """MIL instances are auscultation locations, label belongs to the whole patient."""
    def __init__(self, records, cache_dir, sample_rate=2000, hop=128, crop_seconds=5.,
                 max_recordings=4, train=False, eval_offset=.5):
        self.records = records
        self.cache_dir = Path(cache_dir)
        self.train = train
        self.eval_offset = eval_offset
        self.max_recordings = max_recordings
        self.crop_frames = max(1, int(round(crop_seconds * sample_rate / hop)))
        self.frequency_bins = None
        first = self.cache_dir / (Path(records[0]['paths'][0]).stem + '.npz')
        if not first.exists():
            raise FileNotFoundError(f'Missing spectrogram cache: {first}. Run prepare first.')
        self.frequency_bins = int(_read_cached(str(first)).shape[0])
    def __len__(self):
        return len(self.records)
    def __getitem__(self, ix):
        rec = self.records[ix]
        paths = rec['paths']
        if self.train and len(paths) > self.max_recordings:
            paths = random.sample(paths, self.max_recordings)
        else:
            paths = paths[:self.max_recordings]
        images = np.zeros((self.max_recordings, 1, self.frequency_bins, self.crop_frames), dtype='float32')
        valid = np.zeros(self.max_recordings, dtype='bool')
        for j, path in enumerate(paths):
            matrix = _read_cached(str(self.cache_dir / (Path(path).stem + '.npz')))
            width = matrix.shape[1]
            if width > self.crop_frames:
                start = random.randint(0, width - self.crop_frames) if self.train else int((width-self.crop_frames)*self.eval_offset)
                cropped = matrix[:, start:start+self.crop_frames]
            else:
                cropped = matrix
            images[j, 0, :, :cropped.shape[1]] = cropped
            valid[j] = True
        return (images, valid, np.float32(rec['label']), rec['patient_id'])
