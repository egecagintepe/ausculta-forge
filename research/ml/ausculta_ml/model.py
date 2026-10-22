"""Attention-pooled multi-instance CNN for patient-level murmur research classification."""
import torch
from torch import nn


class ConvUnit(nn.Module):
    def __init__(self, inp, out):
        super().__init__()
        self.net = nn.Sequential(nn.Conv2d(inp, out, 3, padding=1, bias=False),
                                 nn.BatchNorm2d(out), nn.SiLU(inplace=True),
                                 nn.Conv2d(out, out, 3, padding=1, bias=False),
                                 nn.BatchNorm2d(out), nn.SiLU(inplace=True),
                                 nn.MaxPool2d(2))
    def forward(self, x):
        return self.net(x)


class MurmurMIL(nn.Module):
    """Per-auscultation spectrogram encoder + masked patient attention pooling.

    Output logits are *research-only patient-level murmur labels* (present/absent),
    not arrhythmia, diagnosis, or measurement of physical microphone validity.
    """
    def __init__(self, channels=1, embedding=128):
        super().__init__()
        self.encoder = nn.Sequential(
            ConvUnit(channels, 16), ConvUnit(16, 32), ConvUnit(32, 64),
            ConvUnit(64, 96), nn.AdaptiveAvgPool2d((1, 1)), nn.Flatten(),
            nn.Linear(96, embedding), nn.LayerNorm(embedding), nn.SiLU())
        self.attention = nn.Sequential(nn.Linear(embedding, 64), nn.Tanh(), nn.Linear(64, 1))
        self.head = nn.Sequential(nn.LayerNorm(embedding), nn.Dropout(.25), nn.Linear(embedding, 1))

    def forward(self, recordings, mask):
        # recordings [batch, up-to-M locations, channel, frequency, time]
        b, m, c, f, t = recordings.shape
        enc = self.encoder(recordings.reshape(b*m, c, f, t)).reshape(b, m, -1)
        scores = self.attention(enc).squeeze(-1)
        scores = scores.masked_fill(~mask.bool(), torch.finfo(scores.dtype).min)
        weights = torch.softmax(scores, dim=1)
        pooled = (weights.unsqueeze(-1) * enc).sum(1)
        return self.head(pooled).squeeze(-1)
