#!/usr/bin/env python3
"""Offline validator and small HTTP CLI for the Seedance 2.0 family."""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import quote

BASE_URL = "https://argolink.io/v1"
USER_AGENT = "seedance-2-0-skill/1.0"
RATIOS = {"21:9", "16:9", "4:3", "1:1", "3:4", "9:16"}
MODELS = {
    "seedance-2.0": {"resolutions": {"480p", "720p", "1080p", "4k"}, "price": {"480p": .053, "720p": .11, "1080p": .28, "4k": .58}},
    "seedance-2.0-fast": {"resolutions": {"480p", "720p"}, "price": {"480p": .042, "720p": .091}},
    "seedance-2.0-mini": {"resolutions": {"480p", "720p"}, "price": {"480p": .026, "720p": .057}},
}


def check(body: dict) -> tuple[list[str], dict]:
    problems: list[str] = []
    if not isinstance(body, dict):
        return ["request must be a JSON object"], {}
    model = body.get("model")
    spec = MODELS.get(model)
    if spec is None:
        problems.append(f"model must be one of {', '.join(MODELS)}")
    prompt = body.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        problems.append("prompt is required")
    elif len(prompt.encode()) > 20_000:
        problems.append("prompt must be at most 20,000 bytes")
    duration = body.get("duration")
    if type(duration) is not int or not 4 <= duration <= 15:
        problems.append("duration must be an integer from 4 to 15 seconds")
    resolution = body.get("resolution")
    if spec and resolution not in spec["resolutions"]:
        problems.append(f"{model} renders {', '.join(sorted(spec['resolutions']))}; got {resolution!r}")
    if body.get("aspect_ratio") not in RATIOS:
        problems.append("aspect_ratio must be one of 21:9, 16:9, 4:3, 1:1, 3:4, 9:16")
    counts = {"reference_images": 0, "reference_videos": 0, "reference_audios": 0}
    for field, limit in counts.items():
        values = body.get(field, [])
        if not isinstance(values, list):
            problems.append(f"{field} must be an array")
            continue
        counts[field] = len(values)
        if len(values) > {"reference_images": 9, "reference_videos": 3, "reference_audios": 3}[field]:
            problems.append(f"{field} exceeds its limit")
        for item in values:
            if not isinstance(item, dict) or not isinstance(item.get("url"), str) or not item["url"].startswith("https://"):
                problems.append(f"{field} items must contain HTTPS url values")
    if sum(counts.values()) > 15:
        problems.append("references may contain at most 15 assets in total")
    if body.get("end_image") and not body.get("start_image"):
        problems.append("end_image requires start_image")
    if body.get("omni_reference_task_type") or body.get("edit_video"):
        problems.append("Seedance 2.0 has no edit mode in the checked model contract")
    report = {"model": model, "resolution": resolution, "duration": duration,
              "usd": round((duration or 0) * (spec["price"].get(resolution, 0) if spec else 0), 4),
              "reference_counts": counts}
    return problems, report


def read_body(path: str) -> dict:
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read JSON request {path}: {exc}") from exc
    problems, _ = check(value)
    if problems:
        raise ValueError("; ".join(problems))
    return value


class APIError(RuntimeError):
    pass


class Client:
    def __init__(self, api_key: str | None = None, base_url: str | None = None, timeout: float = 120):
        self.api_key = api_key or os.environ.get("SEEDANCE_API_KEY")
        if not self.api_key:
            raise APIError("set SEEDANCE_API_KEY; check does not need a key")
        self.base_url = (base_url or os.environ.get("SEEDANCE_BASE_URL", BASE_URL)).rstrip("/")
        self.timeout = timeout

    def request(self, method: str, path: str, body: dict | None = None, raw: bool = False):
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(self.base_url + path, data=data, method=method)
        request.add_header("Authorization", f"Bearer {self.api_key}")
        request.add_header("User-Agent", USER_AGENT)
        if data is not None:
            request.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                payload = response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")[:500]
            raise APIError(f"{method} {path}: HTTP {exc.code}: {detail}") from None
        except urllib.error.URLError as exc:
            raise APIError(f"{method} {path}: {exc.reason}") from None
        return payload if raw else json.loads(payload)

    def upload(self, path: str, kind: str, content_type: str) -> str:
        data = Path(path).read_bytes()
        ticket = self.request("POST", "/media/uploads", {"model": "seedance-2.0", "type": kind,
            "content_type": content_type, "size_bytes": len(data)})
        put = urllib.request.Request(ticket["upload_url"], data=data, method="PUT")
        put.add_header("Content-Type", content_type)
        put.add_header("User-Agent", USER_AGENT)
        with urllib.request.urlopen(put, timeout=max(self.timeout, 300)):
            pass
        return ticket["media_url"]

    def submit(self, body: dict) -> str:
        return self.request("POST", "/videos/generations", body)["request_id"]

    def status(self, request_id: str) -> dict:
        return self.request("GET", f"/videos/{quote(request_id, safe='-_')}")

    def download(self, request_id: str, destination: str) -> None:
        data = self.request("GET", f"/videos/{quote(request_id, safe='-_')}/content", raw=True)
        target = Path(destination); target.parent.mkdir(parents=True, exist_ok=True)
        part = target.with_suffix(target.suffix + ".part"); part.write_bytes(data); part.replace(target)

    def wait(self, request_id: str, poll_seconds: float = 10, max_polls: int = 360) -> dict:
        for _ in range(max_polls):
            job = self.status(request_id); state = job.get("status")
            if state in {"done", "failed", "expired"}:
                return job
            if state != "pending":
                raise APIError(f"unknown job status {state!r}")
            time.sleep(poll_seconds)
        raise APIError(f"{request_id} is still pending; run wait again, do not submit another job")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    check_cmd = sub.add_parser("check"); check_cmd.add_argument("request")
    submit_cmd = sub.add_parser("submit"); submit_cmd.add_argument("request")
    status_cmd = sub.add_parser("status"); status_cmd.add_argument("request_id")
    wait_cmd = sub.add_parser("wait"); wait_cmd.add_argument("request_id"); wait_cmd.add_argument("--poll", type=float, default=10); wait_cmd.add_argument("--max-polls", type=int, default=360)
    download_cmd = sub.add_parser("download"); download_cmd.add_argument("request_id"); download_cmd.add_argument("destination")
    args = parser.parse_args(argv)
    try:
        if args.command == "check":
            body = json.loads(Path(args.request).read_text(encoding="utf-8")); problems, report = check(body)
            print(json.dumps({"valid": not problems, "problems": problems, "report": report}, indent=2)); return 0 if not problems else 2
        client = Client()
        if args.command == "submit": print(client.submit(read_body(args.request)))
        elif args.command == "status": print(json.dumps(client.status(args.request_id), indent=2))
        elif args.command == "wait": print(json.dumps(client.wait(args.request_id, args.poll, args.max_polls), indent=2))
        elif args.command == "download": client.download(args.request_id, args.destination); print(args.destination)
    except (OSError, ValueError, APIError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr); return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
