"""AuscultaForge — CLI Server Entrypoint for Python Desktop Bridge."""

import argparse
import sys
import uvicorn

from .app import create_app


def main() -> None:
    parser = argparse.ArgumentParser(description="AuscultaForge Desktop Application Bridge Server")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host interface (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind (default: 8000)")
    parser.add_argument("--sessions-dir", type=str, default="experiments/sessions", help="Path to sessions directory")
    args = parser.parse_args()

    app = create_app(sessions_dir=args.sessions_dir)
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
