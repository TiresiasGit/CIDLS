"""
Flask dev server for CIDLS OCR test page.
Usage: uv run python fixtures/web/server.py [--port 8765]
Playwright E2E: http://localhost:8765/?layout=form
"""
import argparse
import sys
from pathlib import Path

try:
    from flask import Flask, send_from_directory
except ImportError as exc:
    raise SystemExit("flask not installed. Run: uv add flask") from exc

FIXTURES_DIR = Path(__file__).parent
app = Flask(__name__)


@app.route("/")
def index():
    return send_from_directory(str(FIXTURES_DIR), "ocr_test_target.html")


@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(str(FIXTURES_DIR), filename)


def main(argv=None):
    parser = argparse.ArgumentParser(description="CIDLS OCR test page server")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args(argv)
    print(f"[CIDLS OCR Server] http://{args.host}:{args.port}/", flush=True)
    app.run(host=args.host, port=args.port, debug=False, use_reloader=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
