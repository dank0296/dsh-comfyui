#!/usr/bin/env python3
"""DSH helper: talk to Spark ComfyUI (:8188) to queue workflows and pull outputs.

WHERE: VPS host or DSH playground. Needs tunnel 127.0.0.1:8188 -> Spark Comfy.

Usage:
  python3 comfy_run.py health
  python3 comfy_run.py queue --workflow /path/to/api.json [--wait]
  python3 comfy_run.py wait PROMPT_ID
  python3 comfy_run.py pull PROMPT_ID --out-dir ./out
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE = os.environ.get("COMFY_URL", "http://127.0.0.1:8188").rstrip("/")


def req(method: str, path: str, data=None, timeout=60):
    body = None
    headers = {}
    if data is not None:
        body = json.dumps(data).encode()
        headers["Content-Type"] = "application/json"
    r = urllib.request.Request(BASE + path, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            raw = resp.read()
            ctype = resp.headers.get("Content-Type", "")
            if "json" in ctype or raw[:1] in (b"{", b"["):
                return json.loads(raw.decode() or "null")
            return raw
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", "replace")[:800]
        raise SystemExit(f"HTTP {e.code} {path}: {err}") from e
    except urllib.error.URLError as e:
        raise SystemExit(f"Comfy unreachable at {BASE} ({e})") from e


def cmd_health(_):
    s = req("GET", "/system_stats")
    sys = (s or {}).get("system") or {}
    print(
        json.dumps(
            {
                "ok": True,
                "url": BASE,
                "comfyui": sys.get("comfyui_version"),
                "pytorch": sys.get("pytorch_version"),
            },
            indent=2,
        )
    )


def load_prompt(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if "nodes" in data and "links" in data:
        raise SystemExit(
            "Editor-format workflow. In Comfy: Workflow → Export (API), save that JSON, then queue it."
        )
    if "prompt" in data and isinstance(data["prompt"], dict):
        return data["prompt"]
    # API format is {node_id: {class_type, inputs}}
    if all(isinstance(v, dict) and "class_type" in v for v in data.values()):
        return data
    raise SystemExit("Not a Comfy API workflow JSON.")


def cmd_queue(args):
    prompt = load_prompt(args.workflow)
    extra = {}
    if args.client_id:
        extra["client_id"] = args.client_id
    out = req("POST", "/prompt", {"prompt": prompt, **extra})
    pid = out.get("prompt_id")
    print(json.dumps({"prompt_id": pid, "number": out.get("number")}, indent=2))
    if args.wait and pid:
        cmd_wait(argparse.Namespace(prompt_id=pid, timeout=args.timeout))


def cmd_wait(args):
    deadline = time.time() + args.timeout
    while time.time() < deadline:
        hist = req("GET", f"/history/{args.prompt_id}")
        if args.prompt_id in hist:
            status = (hist[args.prompt_id].get("status") or {}).get("status_str")
            print(json.dumps({"prompt_id": args.prompt_id, "status": status, "done": True}))
            return
        time.sleep(3)
    raise SystemExit(f"timeout waiting for {args.prompt_id}")


def cmd_pull(args):
    hist = req("GET", f"/history/{args.prompt_id}")
    rec = hist.get(args.prompt_id)
    if not rec:
        raise SystemExit("prompt not in history yet")
    os.makedirs(args.out_dir, exist_ok=True)
    saved = []
    for _nid, node_out in (rec.get("outputs") or {}).items():
        for kind in ("gifs", "videos", "images", "audio"):
            for item in node_out.get(kind) or []:
                fn = item.get("filename")
                if not fn:
                    continue
                q = f"/view?filename={urllib.request.quote(fn)}&type={item.get('type', 'output')}&subfolder={urllib.request.quote(item.get('subfolder') or '')}"
                blob = req("GET", q)
                dest = os.path.join(args.out_dir, fn)
                with open(dest, "wb") as f:
                    f.write(blob if isinstance(blob, bytes) else json.dumps(blob).encode())
                saved.append(dest)
    print(json.dumps({"saved": saved}, indent=2))


def main():
    p = argparse.ArgumentParser(description="DSH → ComfyUI on Spark #1")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("health")
    q = sub.add_parser("queue")
    q.add_argument("--workflow", required=True)
    q.add_argument("--wait", action="store_true")
    q.add_argument("--timeout", type=int, default=900)
    q.add_argument("--client-id", default="")
    w = sub.add_parser("wait")
    w.add_argument("prompt_id")
    w.add_argument("--timeout", type=int, default=900)
    pl = sub.add_parser("pull")
    pl.add_argument("prompt_id")
    pl.add_argument("--out-dir", default="./comfy-out")
    args = p.parse_args()
    {"health": cmd_health, "queue": cmd_queue, "wait": cmd_wait, "pull": cmd_pull}[args.cmd](args)


if __name__ == "__main__":
    main()
