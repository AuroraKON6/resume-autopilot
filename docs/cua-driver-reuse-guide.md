# cua-driver Reuse Guide

How to lift the `computer_use` capability that powers the desktop automation in this project (and the in-app cua-driver integration inside Hermes Agent) out of any single harness and reuse it from your own programs, scripts, or other agent clients.

> Background: this project automates web job boards with Playwright. The `computer_use` capability we are talking about here is the *desktop* layer underneath — it drives the user's real GUI (browser, native apps, file dialogs) **in the background**, without stealing the cursor or keyboard focus. It is built on the open-source [cua-driver](https://github.com/trycua/cua) project, not on any vendor-locked vendor API.

## What `computer_use` actually is

Three layers, top to bottom:

```
┌──────────────────────────────────────────────┐
│  LLM decision layer                          │
│  - Reads a screenshot + numbered SOM overlay │
│  - Or reads the raw AX accessibility tree    │
│  - Returns: "click element #7"               │
└──────────┬───────────────────────────────────┘
           │  computer_use(action="click", element=7)
┌──────────▼───────────────────────────────────┐
│  Hermes wrapper / your wrapper               │
│  - Action vocabulary: click/type/...         │
│  - Renders SOM overlay                       │
│  - Resolves element index → window coords    │
│  - Enforces type-text safety blacklist       │
└──────────┬───────────────────────────────────┘
           │  MCP / HTTP / IPC
┌──────────▼───────────────────────────────────┐
│  cua-driver (cross-platform plumbing)        │
│  - macOS:  AX API + CGEvent injection        │
│  - Windows: UIA + SendInput / UIA Invoke    │
│  - Linux:  AT-SPI + X11/Wayland injection   │
└──────────────────────────────────────────────┘
```

The two non-obvious things cua-driver does that a vanilla PyAutoGUI/AutoIt setup does not:

1. **Reads the UI through the OS accessibility tree**, not OCR.
   - macOS → `AXUIElement`
   - Windows → **UIA (UI Automation)**
   - Linux → **AT-SPI**
   That is why `mode="ax"` can drive a GUI from a text-only LLM with no vision at all.
2. **Injects input events into a specific window handle**, bypassing the system cursor queue. The user's real cursor and keyboard focus are not touched, so the user can keep typing in another window while the agent clicks in a third.

## Why this is reusable

`computer_use` is **not** a Hermes-only feature. cua-driver is its own project, MIT-licensed, designed from day one to be embedded. You can use it from:

- Any MCP-compatible client (Claude Desktop, Cursor, Cline, Zed, Continue, ...)
- Your own Python agent (SDK)
- A shell script or cron job (CLI)
- Any language that can speak MCP-over-HTTP (Go, Rust, C#, Java, ...)

## Four integration paths

### 1. MCP server (most generic)

cua-driver is itself an MCP server. Configure it once and any MCP client can use it.

`~/.config/cua/config.toml` (Linux/macOS) or `%APPDATA%\cua\config.toml` (Windows):

```toml
[[mcp_servers]]
name = "cua-driver"
command = ["cua-driver", "mcp", "serve"]
```

Tool name exposed to the client: `computer` (low-level — `screenshot`, `click`, `type`, ...). Hermes' `computer_use` tool is a higher-level wrapper around the same primitives.

### 2. Python SDK (embed in your own agent)

```bash
pip install cua-computer
```

```python
import asyncio
from cua import Computer

async def fill_form():
    async with Computer(os_type="darwin", name="Safari") as c:
        # screenshot + AX tree in parallel
        shot, tree = await asyncio.gather(
            c.screenshot(mode="som"),
            c.ax_tree(),
        )

        # find a field by its accessibility label
        u = next(n for n in tree if "username" in n.get("label", "").lower())

        await c.click(element=u["id"])
        await c.type("alice@example.com")
        await c.key("tab")
        await c.type("hunter2")
        await c.key("return")

asyncio.run(fill_form())
```

The SDK speaks MCP under the hood — local driver runs as a subprocess, remote driver over HTTP/WebSocket.

### 3. CLI (no LLM, just shell)

```bash
cua-driver screenshot --app Chrome --out shot.png
cua-driver click --app Chrome --element 7
cua-driver type "hello"
cua-driver doctor          # health check
cua-driver skills install  # install cua-driver's own skill pack
```

Good fit for cron jobs, watchdog scripts, "screenshot the dashboard every morning" tasks. No model, no tokens.

### 4. Protocol level (any language)

cua-driver runs an MCP-over-HTTP/SSE server, default `http://127.0.0.1:8443`. Any language that can do HTTP can drive it — ideal when you want to keep the driver in its own process and the consumer in C#/Go/Rust/Java.

## Pick by use case

| Scenario | Pick |
|---|---|
| Plug into Claude Desktop / Cursor | MCP server |
| Embed in our own Python agent | SDK |
| Cron "click this button daily" | CLI |
| Integrate from non-Python code | HTTP/SSE |
| Embed in a deliverable, hide the driver | Subprocess SDK from inside your app |

## Five facts that bite people

1. **It is a background driver, not a foreground RPA.** Target window does not need to be frontmost, real cursor does not move, keyboard focus stays put. But the driver process must share the desktop session with the target GUI — see #2.

2. **Windows Session 0 isolation.** If cua-driver runs as a Windows service or inside an SSH session (Session 0), it cannot see any GUI window and `cua-driver doctor` reports "no on-screen window". It must run inside the **interactive user session**. The reliable pattern is Task Scheduler with **"Run only when user is logged on"** + a startup trigger.

3. **No model bundled.** cua-driver is a driver, not an agent. Model selection is upstream — OpenAI, Anthropic, GLM, Qwen-VL, anything that takes a screenshot and returns tool calls. Pair vision models with `mode="som"`, pair text-only models with `mode="ax"`.

4. **Licensing.** The cua-driver core is MIT (commercial-friendly). The Computer SDK and the `cua-computer` sandbox VM are dual-licensed MIT + commercial. SAAS / resale usage needs the commercial terms read once.

5. **SOM element indices are single-use.** They are only valid for the capture they came from. Re-capture before every click. Hermes' wrapper uses opaque `element_token`s and returns an explicit "stale" error if you try to use an expired index; roll your own equivalent if you skip the Hermes wrapper.

## Minimal working example

A Python agent that opens a page, finds the search field, types a query, and submits — works in ~30 lines:

```python
# pip install cua-computer pillow
import asyncio
from cua import Computer

async def main():
    async with Computer(os_type="darwin", name="Safari") as c:
        await c.navigate("https://example.com")

        tree = await c.ax_tree()
        box = next(n["box"] for n in tree if n.get("label") == "Search")

        await c.click(box=box)
        await c.type("cua-driver")
        await c.key("return")

asyncio.run(main())
```

## How this maps to our project

This repo (`resume-autopilot`) currently automates web job boards with Playwright. cua-driver is the right tool to add when:

- We need to drive a **native** app (e.g. a desktop ATS client) the user has installed.
- We need to operate a browser **without owning the page** (e.g. helping the user with their own logged-in Chrome session, not a headless Playwright instance).
- We need OCR/Vision fallback when a platform's DOM is too dynamic for Playwright (e.g. canvas-rendered login flows).

For everything that stays inside the web (采集/投递 BOSS/智联/51Job/猎聘), keep using Playwright. Mix the two: Playwright for the data plane, cua-driver for the human-side assist plane.

## Going deeper

- cua-driver repo: <https://github.com/trycua/cua>
- cua-driver skill pack (cross-platform, macOS/Windows/Linux deep dives, recording, browser-page tips): `cua-driver skills install`
- Hermes' own `computer-use` skill (action vocabulary + safety rules): the `computer-use` skill in this Hermes instance.
