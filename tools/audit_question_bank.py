import re
from pathlib import Path

content = Path("docs/engineering/defense/QUESTION_BANK.md").read_text(encoding="utf-8")
q_blocks = re.findall(r"### Q(\d+):\s*(.*?)\n(.*?)(?=### Q\d+:|---\s*## Domain|\Z)", content, re.DOTALL)

print(f"Total question blocks: {len(q_blocks)}")

missing_files = []
for qnum, title, block in q_blocks:
    code_ref_match = re.search(r"\*\s*\*\*Code Reference:\*\*\s*(.*)", block)
    ref = code_ref_match.group(1).strip() if code_ref_match else "None"
    
    # Extract backtick paths
    tokens = re.findall(r"`([^`]+)`", ref)
    for t in tokens:
        # ignore function names or generic terms like ISO C99, int32_t, etc.
        if "/" in t or "\\" in t or t.endswith(".py") or t.endswith(".md") or t.endswith(".h") or t.endswith(".c") or t.endswith(".ts") or t.endswith(".json"):
            # strip parenthesis like (generate_pcm_sine)
            clean_path = t.split("(")[0].strip()
            # check path existence
            p = Path(clean_path)
            if not p.exists():
                missing_files.append((qnum, clean_path, ref))

print(f"Missing file references count: {len(missing_files)}")
for qnum, p, ref in missing_files:
    print(f"Q{qnum}: {p} | Ref: {ref}")
