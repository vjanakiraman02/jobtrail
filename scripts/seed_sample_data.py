"""Load the fake applications in sample_data/ into a running JobTrail API.

Usage:
    python scripts/seed_sample_data.py [--api http://localhost:8000] [--force]

Uses only the standard library, so no virtualenv is needed.
"""

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

SAMPLE_FILE = (
    Path(__file__).resolve().parent.parent / "sample_data" / "applications.json"
)


def call(method: str, url: str, payload: dict | None = None):
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(
        url, data=data, method=method, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        body = response.read()
        return json.loads(body) if body else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--api", default="http://localhost:8000", help="API base URL")
    parser.add_argument(
        "--force", action="store_true", help="seed even if data already exists"
    )
    args = parser.parse_args()

    endpoint = f"{args.api.rstrip('/')}/api/v1/applications"
    try:
        existing = call("GET", f"{endpoint}?limit=1")
        if existing and not args.force:
            print(
                "The database already has applications. Re-run with --force to add samples anyway."
            )
            return 1
        samples = json.loads(SAMPLE_FILE.read_text())
        for sample in samples:
            call("POST", endpoint, sample)
    except urllib.error.URLError as error:
        print(f"Could not reach the API at {args.api}: {error}")
        return 1

    print(f"Added {len(samples)} sample applications.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
