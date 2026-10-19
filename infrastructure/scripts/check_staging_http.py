"""Bounded, read-only public smoke checks. Never sends AI calls or login credentials."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import time
import urllib.error
import urllib.parse
import urllib.request


def check(base, path, expected):
    started = time.monotonic()
    try:
        request = urllib.request.Request(base + path, headers={"User-Agent": "Socratia-staging-check/1"})
        try:
            response = urllib.request.urlopen(request, timeout=10)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            body = response.read(65536)
            secure = urllib.parse.urlsplit(response.url).scheme == "https"
            status = response.status
            content_type = response.headers.get("Content-Type", "")
            valid_body = bool(body)
            if path == "/health":
                try:
                    valid_body = "json" in content_type and isinstance(json.loads(body), dict)
                except (ValueError, UnicodeError):
                    valid_body = False
            if path == "/login":
                valid_body = "text/html" in content_type and b"<html" in body.lower()
            return {"path": path, "status": status, "https": secure,
                    "ok": status in expected and secure and valid_body,
                    "elapsed_ms": round((time.monotonic() - started) * 1000)}
    except (OSError, ValueError) as error:
        return {"path": path, "ok": False, "error": type(error).__name__}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    parsed = urllib.parse.urlsplit(args.url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ("", "/"):
        parser.error("Provide an HTTPS origin without credentials, path, query or fragment.")
    base = args.url.rstrip("/")
    cases = [("/health", {200}), ("/login", {200}), ("/api/v1/profile", {401, 403})]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda case: check(base, *case), cases))
    report = {"origin": base, "read_only": True, "ai_calls": 0,
              "ok": all(result["ok"] for result in results), "checks": results}
    rendered = json.dumps(report, indent=2)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
