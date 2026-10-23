"""Guided safe first-contact CLI. A port choice never authorizes a firmware write."""
import argparse
import json
import re
from pathlib import Path
import subprocess
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"software"))
from pcg_app.hardware_workflow import (ROOT, preflight, build_release, validate_release,
    physical_g1, run, write_json, sdk_python)


def confirm_port(port, prompt=input):
    ports=preflight()["ports"]
    selected=next((p for p in ports if p["port_name"].casefold()==port.casefold()),None)
    if selected is None:
        raise ValueError("Selected port is absent. Rescan after BOOT/RESET or USB re-enumeration.")
    print(json.dumps(selected,indent=2))
    if prompt(f"Inspect the PCB and connector; close competing monitors. Type {port} to identify this board: ").strip()!=port:
        raise RuntimeError("Board identification not confirmed; no port opened.")
    return {"status":"OPERATOR_SELECTED_PORT", "enumeration":selected,
            "pcb_revision":"PHYSICAL_INSPECTION_REQUIRED"}


def identify(port):
    outputs=[]
    for action in ("chip_id","flash_id"):
        result=run([sdk_python(),"-m","esptool","--chip","esp32s3","--port",port,
                    "--after","no_reset",action])
        outputs.append(result.stdout+result.stderr)
        if result.returncode:
            raise RuntimeError("Identity query failed; enter BOOT/RESET download mode and retry.\n"+outputs[-1])
    text="\n".join(outputs)
    if "ESP32-S3" not in text or "16MB" not in text.replace(" ",""):
        raise RuntimeError("Expected ESP32-S3 / 16 MB flash not positively identified.\n"+text)
    macs=set(m.lower() for m in re.findall(r"MAC:\s*([0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5})",text))
    if len(macs)!=1:
        raise RuntimeError("Stable chip MAC not identified across ROM queries; do not flash.")
    return {"status":"ROM_IDENTIFIED_ESP32S3_16MB", "port":port,"rom_evidence":text,
            "chip_mac":macs.pop(),
            "psram":"MODULE_MARKING_AND_BOOT_CHECK_REQUIRED"}


def flash(port, manifest_path, prompt=input):
    board=confirm_port(port,prompt)
    board.update(identify(port))
    manifest=validate_release(manifest_path)
    base=Path(manifest["build_directory"])
    files=manifest["flash_files"]
    if set(files.values()) != set(manifest["binary_sha256"]):
        raise ValueError("Flash files do not exactly match verified hashes")
    if sorted(int(offset,0) for offset in files) != [0,0x8000,0x10000]:
        raise ValueError("Unexpected partition write offsets; review the release")
    print(f"Verified build: {manifest['commit']} / {manifest['firmware_version']}")
    if prompt(f"Confirm N16R8 module marking and inspected power routing. This overwrites bootloader, partition table and application. Type FLASH {port} to authorize: ").strip()!=f"FLASH {port}":
        raise RuntimeError("Flash not authorized; no firmware written.")
    validate_release(manifest_path)  # Recheck hashes after the operator's review.
    if identify(port)["chip_mac"] != board["chip_mac"]:
        raise RuntimeError("Device identity changed during confirmation; no firmware written.")
    command=[sdk_python(),"-m","esptool","--chip","esp32s3","--port",port,
             "write_flash","--flash_mode","dio","--flash_freq","80m","--flash_size","16MB"]
    for offset,name in files.items():
        command += [offset,str(base/name)]
    result=subprocess.run(command,capture_output=True,text=True,timeout=180)
    (base/"first-flash.txt").write_text(result.stdout+result.stderr,encoding="utf-8")
    write_json(base/"board_identity.json",board)
    if result.returncode:
        raise RuntimeError("Flash failed. Preserve first-flash.txt; use verified BOOT/RESET ROM recovery. No erase/eFuse operations.")
    print("Flash completed, physical boot NOT YET VERIFIED. Native USB may disappear and return with a NEW COM number. Rescan before HELLO.")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest="action")
    sub.add_parser("preflight")
    sub.add_parser("build")
    for action in ("identify","flash","hello","g1"):
        p=sub.add_parser(action)
        p.add_argument("--port",required=True)
        if action=="flash":
            p.add_argument("--manifest",type=Path,default=ROOT/"firmware/build/release/firmware_build_manifest.json")
        if action=="g1":
            p.add_argument("--output",type=Path,default=ROOT/"experiments/hardware")
            p.add_argument("--manifest",type=Path,default=ROOT/"firmware/build/release/firmware_build_manifest.json")
    args=parser.parse_args()
    try:
        if args.action is None:
            print("DISCOVER → IDENTIFY → CONFIRM → FLASH → BOOT → USB DETECT → HELLO → G1 → EXPORT")
            print(json.dumps(preflight(),indent=2))
            print("Run build; then flash --port <verified ROM COM>. Flash always asks a second explicit confirmation.\nAfter reboot: hello --port <new CDC COM>, then g1 --port <CDC COM>.")
        elif args.action=="preflight":
            print(json.dumps(preflight(),indent=2))
        elif args.action=="build":
            print(json.dumps(build_release(),indent=2))
        elif args.action=="flash":
            flash(args.port,args.manifest)
        else:
            board=confirm_port(args.port)
            if args.action=="identify":
                print(json.dumps(identify(args.port),indent=2))
            elif args.action=="hello":
                from pcg_app.canonical.engine import CanonicalSessionEngine
                engine=CanonicalSessionEngine()
                try:
                    print(engine.connect(args.port).result(timeout=5))
                    print("FIRMWARE HANDSHAKE VERIFIED. G1 still NOT_EXECUTED.")
                finally:
                    engine.disconnect().result(timeout=5)
            else:
                manifest=validate_release(args.manifest) if args.manifest else None
                identity_path=args.manifest.parent/"board_identity.json"
                if identity_path.is_file():
                    board["rom_identity"]=json.loads(identity_path.read_text(encoding="utf-8"))
                evidence,directory=physical_g1(args.port,args.output,board,manifest)
                print(evidence["conclusion"],directory)
                return 0 if evidence["conclusion"]=="PHYSICAL_G1_PASSED" else 1
    except (ValueError,RuntimeError,TimeoutError,ConnectionError,OSError,subprocess.SubprocessError) as exc:
        print(f"INCOMPLETE: {exc}",file=sys.stderr)
        return 1
    return 0


if __name__=="__main__":
    raise SystemExit(main())
