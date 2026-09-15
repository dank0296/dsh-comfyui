# Spark / DSH wiring (dank0296 fork)

This repo is a **public fork** of [fandc520/dsh-comfyui](https://github.com/fandc520/dsh-comfyui) **v0.5.1** (`9592a9d`). MIT. Full **agent tools + ComfyUI panel UI** kept.

Not affiliated with DeepSeek or fandc520.

## What we kept

- DSH web panel (workflows / assets / queue)
- Agent tools: `comfyui_run`, `comfyui_workflow`, `comfyui_object_info`, `comfyui_skill`
- Media proxy so the browser never talks to Comfy directly

## Dank layout

| Piece | Where |
|-------|--------|
| DSH | srv1710004 `127.0.0.1:3080` |
| Comfy | Spark #1 `comfyui-spark` **:8188** (LTX-2.3) |
| Tunnel | host `dsh-spark-8188.service` → `127.0.0.1:8188` |
| FAST | Spark #1 `:8080` — LTX jobs can knock it; park Comfy after |

Settings → ComfyUI → server `http://127.0.0.1:8188`

Built-in **video** template is **Wan**. Our clips use **LTX-2.3**: export API JSON from Comfy (or Extract in the panel) and run that.

## Extra CLI (no DSH UI)

`python3 extra/comfy_run.py health` — playground fallback if the plugin is off.

## Install (do not pnpm the harness checkout)

```
dsh plugin --profile web add github:dank0296/dsh-comfyui#master
```

Pin when you care: `#9592a9d` or a later tag on this fork.

Headless VPS: panel **Reveal folder** uses `xdg-open` and will no-op. That is fine.
