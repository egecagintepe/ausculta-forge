import os
import re
from pathlib import Path

docs_dir = Path("docs/engineering")
md_files = list(docs_dir.rglob("*.md"))
print(f"Total markdown files in docs/engineering: {len(md_files)}")

# Patterns to scan for
patterns = {
    "transport.py": re.compile(r"software/pcg_app/transport\.py"),
    "pcg_app/device/": re.compile(r"software/pcg_app/device/"),
    ".meta.json": re.compile(r"\.meta\.json"),
    "generate_sine_100hz_sample": re.compile(r"generate_sine_100hz_sample"),
    "pack_and_align_sample": re.compile(r"pack_and_align_sample"),
    "portable_generator": re.compile(r"portable_generator"),
    "esp32_bench_example_main.c": re.compile(r"esp32_bench_example_main\.c"),
    "100% verified": re.compile(r"100%\s*verified", re.IGNORECASE),
    "/api/device/open": re.compile(r"/api/device/open\b"),
    "/api/device/close": re.compile(r"/api/device/close\b"),
    "/api/stream/metrics": re.compile(r"/api/stream/metrics\b"),
    "/api/analysis/spectral": re.compile(r"/api/analysis/spectral\b"),
    "/api/analysis/envelopes": re.compile(r"/api/analysis/envelopes\b"),
    "/api/metrology/run_all": re.compile(r"/api/metrology/run_all\b"),
    "/api/bench/load": re.compile(r"/api/bench/load\b"),
    "/api/bench/run_all": re.compile(r"/api/bench/run_all\b"),
    "/api/research/segment": re.compile(r"/api/research/segment\b"),
    "/api/research/validate": re.compile(r"/api/research/validate\b"),
    "/api/ws/stream": re.compile(r"/api/ws/stream\b"),
    "bridgeClient.ts (wrong path)": re.compile(r"software/frontend/src/bridgeClient\.ts"),
}

findings = {k: [] for k in patterns}

for f in md_files:
    text = f.read_text(encoding="utf-8")
    for name, pat in patterns.items():
        matches = pat.findall(text)
        if matches:
            findings[name].append((f, len(matches)))

for name, occurrences in findings.items():
    if occurrences:
        print(f"\n[FLAG] {name}: {sum(count for _, count in occurrences)} hits in {len(occurrences)} files:")
        for path, count in occurrences:
            print(f"  - {path.relative_to(docs_dir)} ({count} hits)")
    else:
        print(f"[OK] {name}: 0 hits")
