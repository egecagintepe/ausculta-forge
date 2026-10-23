"""Passive Windows/host readiness report; no serial port opens."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"software"))
from pcg_app.hardware_workflow import preflight, write_json

if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path)
    parser.add_argument("--json",action="store_true")
    args=parser.parse_args()
    report=preflight()
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        write_json(args.output,report)
    print(json.dumps(report,indent=2) if args.json else "\n".join(
        f"{key}: {report[key]}" for key in ("BOARD_ATTACHED","ESP_IDF","FIRMWARE_BUILD","USB_CDC_HOST","DESKTOP_BACKEND","HARDWARE_TEST","next_action")))
