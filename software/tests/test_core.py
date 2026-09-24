import numpy as np

from pcg_core.models import SampleBlock
from pcg_core.dsp import StreamingBandpass
from pcg_core.metrics import rms


def test_sample_block():
    b = SampleBlock(0, 0.0, 4000, [0, 1, 2])
    assert b.samples.dtype == np.float32
    assert len(b.samples) == 3


def test_streaming_filter_runs():
    b = SampleBlock(0, 0.0, 4000, np.zeros(256))
    f = StreamingBandpass(4000)
    out = f.process(b)
    assert len(out.samples) == 256
    assert rms(out.samples) == 0.0
