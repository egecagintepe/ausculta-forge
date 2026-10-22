import json
import numpy as np
import pandas as pd
import soundfile as sf
import torch
from ausculta_ml.data import make_index, frozen_split, make_spectrogram
from ausculta_ml.model import MurmurMIL
from ausculta_ml.filter_advisor import recommend_filters, render_filter_preview


def test_mil_mask_shapes():
    model=MurmurMIL()
    x=torch.randn(2,4,1,96,78)
    mask=torch.tensor([[True,True,False,False],[True,False,False,False]])
    with torch.no_grad():out=model(x,mask)
    assert out.shape==(2,)
    assert torch.isfinite(out).all()


def test_no_cross_campaign_patient_leakage(tmp_path):
    # Twelve grouped identities; two aliases map to same person, across campaigns.
    records=[]
    for i in range(36):
        sid=str(i+1000)
        records.append({'patient_id':sid,'additional_id':str(i-1+1000) if i==1 else None,
                        'label':i%2,'paths':['no-file-needed.wav']})
    splits=frozen_split(records,tmp_path/'manifest.json',seed=42,val_fraction=.20,test_fraction=.20)
    owners={p['patient_id']:name for name,s in splits.items() for p in s}
    assert owners['1000']==owners['1001']
    assert all(len(splits[k]) for k in ('train','val','test'))
    # Re-reading same manifest must never reshuffle.
    assert splits==frozen_split(records,tmp_path/'manifest.json',seed=999)


def test_real_csv_schema_and_wave_preprocessing(tmp_path):
    root=tmp_path/'training';(root/'training_data').mkdir(parents=True)
    pd.DataFrame([{'Patient ID':1212,'Murmur':'Present','Recording locations:':'AV',
         'Additional ID':float('nan')},{'Patient ID':1213,'Murmur':'Unknown',
         'Recording locations:':'MV','Additional ID':float('nan')}]).to_csv(root/'training_data.csv',index=False)
    sf.write(root/'training_data/1212_AV.wav',np.sin(np.arange(8000)*2*np.pi*80/4000).astype('float32'),4000)
    records=make_index(root,tmp_path/'index.json')
    assert len(records)==1 and records[0]['label']==1
    spec=make_spectrogram(records[0]['paths'][0])
    assert spec.shape[0]>50 and spec.shape[1]>10 and np.isfinite(spec).all()


def test_filter_advisor_is_conservative_and_non_destructive():
    fs=2000;t=np.arange(fs*4)/fs
    original=(.15*np.sin(2*np.pi*70*t)+.35*np.sin(2*np.pi*50*t)).astype('float32')
    copy=original.copy()
    recs=recommend_filters(original,fs)
    assert any(r.family=='notch_preview' and r.parameters['center_hz']==50 for r in recs)
    candidate=next(r for r in recs if r.family=='notch_preview' and r.parameters['center_hz']==50)
    y=render_filter_preview(original,fs,candidate)
    assert np.array_equal(copy,original)
    assert not np.array_equal(y,original)
