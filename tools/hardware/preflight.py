"""Passive Windows/host readiness report; no serial port opens."""
import argparse
import json
from pathlib import Path
import sys
import importlib.util
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"software"))

if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path)
    parser.add_argument("--json",action="store_true")
    args=parser.parse_args()
    missing=[name for name in ("numpy","scipy","fastapi","uvicorn","serial","pywt")
             if importlib.util.find_spec(name) is None]
    if missing:
        report={"HARDWARE_TEST":"NOT_EXECUTED","BOARD_ATTACHED":"NOT_PROBED",
                "checks":{name:"MISSING" for name in missing},
                "next_action":"Create .venv with Python 3.11+, then .venv/Scripts/python.exe -m pip install -r software/requirements.txt -e ./software. See WINDOWS_LAPTOP_SETUP.md."}
    else:
        from pcg_app.hardware_workflow import preflight
        report=preflight()
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2) if args.json else "\n".join(
        f"{key}: {value}" for key,value in report.items() if key in ("checks","BOARD_ATTACHED","ESP_IDF","FIRMWARE_BUILD","USB_CDC_HOST","DESKTOP_BACKEND","HARDWARE_TEST","next_action")))
