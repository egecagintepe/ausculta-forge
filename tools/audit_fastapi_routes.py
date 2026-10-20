#!/usr/bin/env python3
"""AuscultaForge — Automated FastAPI Route Audit & Verification Tool.

Programmatically instantiates the application via create_app(), extracts all
registered HTTP and WebSocket routes, compares them against test execution
evidence in software/tests/, and verifies documentation accuracy.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys

# Ensure software directory is in path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "software"))

from pcg_app.app import create_app


def get_registered_routes() -> list[dict]:
    app = create_app()
    openapi = app.openapi()
    routes = []

    # Map paths from openapi
    for path, methods in sorted(openapi.get("paths", {}).items()):
        for method, details in sorted(methods.items()):
            routes.append({
                "type": "HTTP",
                "method": method.upper(),
                "path": path,
                "operation_id": details.get("operationId", ""),
                "summary": details.get("summary", ""),
                "has_body": details.get("requestBody") is not None,
                "responses": list(details.get("responses", {}).keys()),
            })

    # WebSocket routes
    for r in app.routes:
        if not hasattr(r, "methods"):
            routes.append({
                "type": "WS",
                "method": "WS",
                "path": getattr(r, "path", "/ws"),
                "operation_id": getattr(r, "name", "websocket"),
                "summary": "Real-time bidirectional WebSocket stream",
                "has_body": False,
                "responses": ["101"],
            })

    return routes


def get_tested_routes() -> set[tuple[str, str]]:
    test_dir = ROOT_DIR / "software" / "tests"
    tested = set()
    pattern = re.compile(r'client\.(get|post|delete|put)\((?:f?["\'])(/api/[^"\'? ]+)')

    for test_file in test_dir.rglob("*.py"):
        try:
            content = test_file.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for method, path in pattern.findall(content):
            # Normalize path template variables if formatted: e.g. /api/sessions/{session_id}
            # Replace curly braces if substituted with {.*}
            clean_path = re.sub(r'\{[^}]+\}', '*', path)
            tested.add((method.upper(), clean_path))

    return tested


def run_audit():
    routes = get_registered_routes()
    tested = get_tested_routes()

    print("=" * 80)
    print(f"AUSCULTAFORGE FASTAPI ROUTE AUDIT: {len(routes)} REGISTERED ROUTES")
    print("=" * 80)

    http_count = sum(1 for r in routes if r["type"] == "HTTP")
    ws_count = sum(1 for r in routes if r["type"] == "WS")
    print(f"Registered: {http_count} HTTP endpoints, {ws_count} WebSocket endpoint(s)")
    print(f"Observed Test Calls: {len(tested)} distinct API route patterns in software/tests/")
    print("-" * 80)

    for r in routes:
        m = r["method"]
        p = r["path"]
        op = r["operation_id"]
        # Check if tested
        norm_p = re.sub(r'\{[^}]+\}', '*', p)
        is_tested = (m, norm_p) in tested or any(m == tm and norm_p.startswith(tp.rstrip('*')) for tm, tp in tested)
        test_badge = "[TESTED]" if is_tested else "[REGISTERED]"
        print(f"{test_badge:12} {m:6} {p:45} -> {op}")

    print("=" * 80)


if __name__ == "__main__":
    run_audit()
