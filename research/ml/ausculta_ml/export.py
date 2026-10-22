"""Safe CPU inference artifact export and model contract declaration."""
from pathlib import Path
import json
import argparse
import torch
from .model import MurmurMIL


def export(run_dir: Path, output_dir: Path):
    run_dir=Path(run_dir);output_dir=Path(output_dir)
    output_dir.mkdir(parents=True,exist_ok=True)
    # Only trust checkpoints produced by our own training code, not random downloads.
    ck=torch.load(run_dir/'checkpoint_best.pt',map_location='cpu',weights_only=False)
    metrics=json.loads((run_dir/'metrics.json').read_text(encoding='utf8'))
    model=MurmurMIL().eval()
    model.load_state_dict(ck['model'])
    cfg=ck['config']
    freqs=torch.fft.rfftfreq(cfg['stft_n_fft'], d=1/cfg['sample_rate'])
    f_bins=int(((freqs>=cfg['band_low_hz']) & (freqs<=cfg['band_high_hz'])).sum().item())
    crop_frames=round(cfg['crop_seconds']*cfg['sample_rate']/cfg['stft_hop'])
    example=torch.zeros((1,cfg['max_recordings'],1,f_bins,crop_frames),dtype=torch.float32)
    mask=torch.zeros((1,cfg['max_recordings']),dtype=torch.bool)
    mask[:,0]=True
    torch.save(model.state_dict(),output_dir/'weights.pt')
    scripted=torch.jit.trace(model,(example,mask),strict=True)
    scripted.save(str(output_dir/'murmur_mil_cpu.pt'))
    with torch.no_grad():
        delta=(scripted(example,mask)-model(example,mask)).abs().max().item()
    if delta>1e-5:raise RuntimeError(f'TorchScript roundtrip mismatch {delta}')
    manifest={'model_version':cfg['model_version'],'format':'torchscript + pytorch weights',
       'input':['batch','recordings','channel','frequency_bins','crop_frames'],
       'input_dtype':'float32','attention_mask':'bool[batch,recordings]',
       'sample_rate':cfg['sample_rate'],'stft_n_fft':cfg['stft_n_fft'],'stft_hop':cfg['stft_hop'],
       'band_low_hz':cfg['band_low_hz'],'band_high_hz':cfg['band_high_hz'],
       'crop_seconds':cfg['crop_seconds'],'max_recordings':cfg['max_recordings'],
       'threshold':metrics['validation_threshold'],'dataset':'CirCor 1.0.3 public training subset',
       'provenance':metrics['provenance'], 'strictly_nonclinical':True,
       'restriction':'Do not show as medical diagnosis or deploy on real acquisition before external and domain validation.'}
    (output_dir/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
    return manifest


def main():
    p=argparse.ArgumentParser();p.add_argument('--run',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();print(json.dumps(export(Path(a.run),Path(a.out)),indent=2))

if __name__=='__main__':main()
