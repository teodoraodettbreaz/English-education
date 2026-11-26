from __future__ import annotations

import argparse
import os

from .config import Settings
from .web import serve


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the PathLex authoring and story server.")
    parser.add_argument("--host", help="Bind host (default: PATHLEX_HOST or 127.0.0.1)")
    parser.add_argument("--port", type=int, help="Bind port (default: PATHLEX_PORT or 8080)")
    args = parser.parse_args()
    if args.host:
        os.environ["PATHLEX_HOST"] = args.host
    if args.port:
        os.environ["PATHLEX_PORT"] = str(args.port)
    serve(Settings.from_env())


if __name__ == "__main__":
    main()

