"""Real full-dataset Colab trainer: immutable group splits, resume, calibrated test protocol."""
from __future__ import annotations
import argparse
import hashlib
import json
import random
import shutil
import sys
import time
from pathlib import Path
import numpy as np
import torch
import yaml
from sklearn.metrics import roc_auc_score, average_precision_score, f1_score, balanced_accuracy_score, confusion_matrix
from torch.utils.data import DataLoader, WeightedRandomSampler
from .data import make_index, frozen_split, prepare_spectrogram_cache, PatientSpectrogramDataset, sha256_file
from .model import MurmurMIL


def seed_everything(seed):
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    if torch.cuda.is_available(): torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def dataloader(dataset, batch_size, training, num_workers=0):
    if training:
        classes = np.array([r['label'] for r in dataset.records])
        counts = np.bincount(classes, minlength=2)
        weights = np.array([1.0 / max(1, counts[int(c)]) for c in classes])
        sampler = WeightedRandomSampler(torch.as_tensor(weights, dtype=torch.double),
                                        num_samples=len(dataset), replacement=True)
    else: sampler = None
    return DataLoader(dataset, batch_size=batch_size, shuffle=False, sampler=sampler,
         num_workers=num_workers, pin_memory=torch.cuda.is_available(),
         persistent_workers=(num_workers > 0))


def scores(y, p, threshold=.5):
    y=np.asarray(y, dtype=int); p=np.asarray(p, dtype=float)
    pred=(p>=threshold).astype(int)
    return {'n_patients': int(len(y)), 'positives': int(y.sum()),
        'roc_auc': float(roc_auc_score(y,p)) if len(set(y)) > 1 else None,
        'average_precision': float(average_precision_score(y,p)) if len(set(y)) > 1 else None,
        'balanced_accuracy': float(balanced_accuracy_score(y,pred)),
        'f1': float(f1_score(y,pred,zero_division=0)),
        'confusion_matrix_tn_fp_fn_tp': confusion_matrix(y,pred,labels=[0,1]).ravel().astype(int).tolist(),
        'threshold': float(threshold)}


def evaluate(model, loader, device, offsets=(.5,)):
    model.eval()
    pred = None
    labels = None
    with torch.no_grad():
        for offset in offsets:
            loader.dataset.eval_offset = offset
            allp, ally = [], []
            for images, mask, label, ids in loader:
                images=images.to(device, non_blocking=True)
                mask=mask.to(device, non_blocking=True)
                logits=model(images, mask)
                allp.extend(logits.float().cpu().tolist()); ally.extend(label.numpy().astype(int).tolist())
            p=np.asarray(allp)
            if pred is None: pred=p
            else: pred += p
            if labels is None: labels=np.asarray(ally, dtype=int)
            elif not np.array_equal(labels, np.asarray(ally, dtype=int)):
                raise RuntimeError('Evaluation sample order changed unexpectedly')
    pred /= len(offsets)
    return labels, torch.sigmoid(torch.as_tensor(pred)).numpy()


def choose_threshold(y, p):
    grid = np.arange(.20, .801, .02)
    # Calibration is performed ONLY on validation predictions.
    return float(max(grid, key=lambda x: (balanced_accuracy_score(y,p>=x), -abs(.5-x))))


def atomic_save(obj, target: Path):
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp=target.with_suffix('.tmp')
    torch.save(obj,tmp)
    tmp.replace(target)


def run(config_path, raw_dir, work_dir, run_dir, resume=False, epochs_override=None):
    cfg=yaml.safe_load(Path(config_path).read_text(encoding='utf8'))
    seed_everything(int(cfg['seed']))
    raw_dir=Path(raw_dir); work_dir=Path(work_dir); run_dir=Path(run_dir)
    work_dir.mkdir(parents=True,exist_ok=True); run_dir.mkdir(parents=True,exist_ok=True)
    index_path=work_dir/'circor_index.json'
    records=make_index(raw_dir,index_path)
    csv_hash=sha256_file(raw_dir/'training_data.csv')
    splits=frozen_split(records,work_dir/'split_manifest.json',int(cfg['seed']),
                        cfg['val_fraction'],cfg['test_fraction'])
    spec_params=dict(sample_rate=cfg['sample_rate'],nfft=cfg['stft_n_fft'],
                  hop=cfg['stft_hop'],low_hz=cfg['band_low_hz'],high_hz=cfg['band_high_hz'])
    cache_dir=work_dir/'spectrogram_cache'
    prepare_spectrogram_cache(records,cache_dir,**spec_params)
    ds_kwargs=dict(cache_dir=cache_dir,sample_rate=cfg['sample_rate'],hop=cfg['stft_hop'],
                   crop_seconds=cfg['crop_seconds'],max_recordings=cfg['max_recordings'])
    loaders={}
    for p in ('train','val','test'):
        ds=PatientSpectrogramDataset(splits[p],train=(p=='train'),**ds_kwargs)
        loaders[p]=dataloader(ds,int(cfg['batch_size']),training=(p=='train'),
              num_workers=int(cfg.get('num_workers',0)) if p=='train' else 0)
    split_stats={part:{'patients':len(rows),'present':sum(r['label'] for r in rows)}
                 for part,rows in splits.items()}
    print('Frozen patient split:',split_stats)
    device=torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print('Device:',device, 'Torch:', torch.__version__)
    model=MurmurMIL().to(device)
    opt=torch.optim.AdamW(model.parameters(),lr=float(cfg['learning_rate']),
                          weight_decay=float(cfg['weight_decay']))
    loss_fn=torch.nn.BCEWithLogitsLoss()
    config_hash=hashlib.sha256(Path(config_path).read_bytes()).hexdigest()
    signature={'config_sha256':config_hash,'csv_sha256':csv_hash,
               'split_sha256':sha256_file(work_dir/'split_manifest.json')}
    start=1; best_auc=-1.; best_epoch=0; bad=0
    last=run_dir/'checkpoint_last.pt'; best=run_dir/'checkpoint_best.pt'
    if resume:
        if not last.exists():raise FileNotFoundError(f'--resume selected but no {last}')
        ck=torch.load(last,map_location='cpu',weights_only=False)
        if ck['signature']!=signature:raise ValueError('Resume data/config/split mismatch')
        model.load_state_dict(ck['model']);opt.load_state_dict(ck['optimizer']);start=ck['epoch']+1
        best_auc=ck['best_auc'];best_epoch=ck['best_epoch'];bad=ck['patience_counter']
        random.setstate(ck['random_state']);np.random.set_state(ck['numpy_state'])
        torch.set_rng_state(ck['torch_rng_state'])
        if device.type=='cuda' and ck.get('cuda_rng_state') is not None:
            torch.cuda.set_rng_state_all(ck['cuda_rng_state'])
        print('Resumed from epoch',start)
    epochs=int(epochs_override or cfg['epochs'])
    history_path=run_dir/'history.jsonl'
    for epoch in range(start,epochs+1):
        model.train(); total=0.; num=0; t0=time.monotonic()
        for images,mask,y,ids in loaders['train']:
            images=images.to(device,non_blocking=True);mask=mask.to(device,non_blocking=True)
            y=y.to(device,non_blocking=True)
            opt.zero_grad(set_to_none=True)
            logits=model(images,mask)
            loss=loss_fn(logits,y)
            loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),2.)
            opt.step();total+=float(loss.detach())*len(y);num+=len(y)
        yv,pv=evaluate(model,loaders['val'],device,offsets=(.5,))
        m=scores(yv,pv);auc=m['roc_auc'] if m['roc_auc'] is not None else -1.
        improved=auc>best_auc+float(cfg.get('min_delta',0))
        if improved:
            best_auc=auc;best_epoch=epoch;bad=0
            atomic_save({'model':model.cpu().state_dict(),'epoch':epoch,'signature':signature,
                         'config':cfg,'val_metrics':m},best)
            model.to(device)
        else:bad+=1
        info={'epoch':epoch,'train_loss':total/max(1,num),'val_auc':auc,
              'val_auprc':m['average_precision'],'duration_s':round(time.monotonic()-t0,1),
              'best_epoch':best_epoch}
        with open(history_path,'a',encoding='utf8') as f:f.write(json.dumps(info)+'\n')
        checkpoint={'model':model.cpu().state_dict(),'optimizer':opt.state_dict(),
                'epoch':epoch,'best_auc':best_auc,'best_epoch':best_epoch,'patience_counter':bad,
                'signature':signature,'random_state':random.getstate(),
                'numpy_state':np.random.get_state(),'torch_rng_state':torch.get_rng_state(),
                'cuda_rng_state':torch.cuda.get_rng_state_all() if torch.cuda.is_available() else None}
        atomic_save(checkpoint,last)
        model.to(device)
        print(json.dumps(info),flush=True)
        if bad>=int(cfg['patience']):
            print('Early stopping (validation only).');break
    if not best.exists():
        raise RuntimeError('No training checkpoint produced; inspect data split and earlier errors.')
    ck=torch.load(best,map_location='cpu',weights_only=False)
    if ck['signature']!=signature:raise ValueError('Best checkpoint does not match this dataset/config/split')
    model.load_state_dict(ck['model']);model.to(device)
    yv,pv=evaluate(model,loaders['val'],device,offsets=(0.,.5,1.))
    threshold=choose_threshold(yv,pv)
    val_report=scores(yv,pv,threshold)
    yt,pt=evaluate(model,loaders['test'],device,offsets=(0.,.5,1.))
    report={'research_only':True, 'no_clinical_claims':True, 'model_version':cfg['model_version'],
            'dataset': 'PhysioNet CirCor 1.0.3 public training subset',
            'patient_group_split':split_stats,'best_epoch':ck['epoch'],
            'validation_threshold':threshold,'validation':val_report,
            'internal_heldout_test':scores(yt,pt,threshold),
            'provenance':signature,'code': 'AuscultaForge research/ml',
            'warning': 'Internal heldout test within CirCor publicly released training patients; no independent clinical validation.'}
    (run_dir/'metrics.json').write_text(json.dumps(report,indent=2),encoding='utf8')
    (run_dir/'training_config.yaml').write_text(Path(config_path).read_text(encoding='utf8'))
    shutil.copy2(work_dir/'split_manifest.json',run_dir/'split_manifest.json')
    (run_dir/'model_card.md').write_text(
        '# AuscultaForge Murmur MIL v1 — Research Only\n\n'
        'Patient-level multi-recording model on CirCor public training subset.\n'
        'No clinical diagnosis, no arrhythmia diagnosis, no extrapolation to ESP32/phantom.\n\n'
        'Train/validation/internal test groups frozen using Additional ID links.\n'
        f'Validation threshold: {threshold:.3f}. Best epoch: {ck["epoch"]}.\n'
        'Limitations: pediatric population, single dataset, unknown labels excluded, unseen hardware domain shift.\n',encoding='utf8')
    print(json.dumps(report,indent=2))
    return report


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--config',required=True)
    parser.add_argument('--raw',required=True)
    parser.add_argument('--work',required=True)
    parser.add_argument('--run',required=True)
    parser.add_argument('--resume',action='store_true')
    parser.add_argument('--epochs',type=int,default=None)
    args=parser.parse_args()
    run(args.config,args.raw,args.work,args.run,args.resume,args.epochs)


if __name__=='__main__': main()
