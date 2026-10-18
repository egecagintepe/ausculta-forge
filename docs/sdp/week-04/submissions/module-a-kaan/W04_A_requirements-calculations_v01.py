"""Week 4 illustrative calculations only. No experimental data are generated."""
import csv
import math
from pathlib import Path

out = Path(__file__).with_name('W04_A_illustrative-highpass_v01.csv')
with out.open('w', newline='', encoding='utf-8') as stream:
    writer = csv.writer(stream)
    writer.writerow(['status', 'frequency_hz', 'assumed_cutoff_hz', 'loss_db'])
    for frequency in [20, 30, 40, 60, 100, 500]:
        loss = 20 * math.log10(frequency / math.sqrt(frequency**2 + 60**2))
        writer.writerow(['ILLUSTRATION_NOT_MEASURED', frequency, 60, f'{loss:.2f}'])
print('I2S proposal BCLK:', 64 * 48000, 'Hz')
print('Proposed 6 dB headroom peak fraction:', 10**(-6/20))
print('Illustrative CSV:', out)
