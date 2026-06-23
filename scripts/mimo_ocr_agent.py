# -*- coding: utf-8 -*-
"""
Mimo + OCR desktop agent for assisted job applications.

Flow:
  screenshot -> OCR -> Mimo decision -> guarded action -> result check -> loop

This agent intentionally stops for login, captcha, security checks, and final
submission unless --auto-submit is passed.
"""

import argparse
import base64
import io
import json
import os
import random
import re
import sys
import time
import webbrowser
from datetime import datetime
from pathlib import Path

import pyautogui
import requests

try:
    import certifi
except Exception:
    certifi = None


pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.25

ROOT = Path(__file__).resolve().parents[1]
SCREENSHOT_DIR = ROOT / "screenshots"

PLATFORM_URLS = {
    "boss": "https://www.zhipin.com/web/geek/job?query={keyword}",
    "51job": "https://we.51job.com/pc/search?keyword={keyword}",
    "zhilian": "https://sou.zhaopin.com/?kw={keyword}",
    "liepin": "https://www.liepin.com/zhaopin/?key={keyword}",
}

PLATFORM_WINDOW_KEYWORDS = {
    "boss": ["boss", "zhipin", "BOSS直聘"],
    "51job": ["51job", "前程无忧"],
    "zhilian": ["zhaopin", "智联"],
    "liepin": ["liepin", "猎聘"],
}

BROWSER_WINDOW_KEYWORDS = [
    "chrome",
    "edge",
    "firefox",
    "browser",
    "浏览器",
    "google chrome",
    "microsoft edge",
]

BLOCKING_KEYWORDS = [
    "captcha",
    "verification",
    "verify",
    "login",
    "sign in",
    "安全验证",
    "人机验证",
    "滑块",
    "验证码",
    "短信验证码",
    "手机验证码",
    "扫码登录",
    "扫码登陆",
    "二维码登录",
    "微信扫码登录",
    "登录",
    "异常访问",
]

FINAL_SUBMIT_KEYWORDS = [
    "apply",
    "submit",
    "send resume",
    "投递",
    "申请",
    "立即沟通",
    "立即申请",
    "发送简历",
    "投递简历",
    "提交申请",
]

SUCCESS_KEYWORDS = [
    "applied",
    "submitted",
    "success",
    "已投递",
    "投递成功",
    "已申请",
    "申请成功",
    "已发送",
    "沟通成功",
    "已沟通",
    "已向BOSS发送消息",
    "已向 Boss 发送消息",
    "向BOSS发送消息",
    "简历已投",
]

BOSS_SUCCESS_DIALOG_KEYWORDS = [
    "已向BOSS发送消息",
    "已向 Boss 发送消息",
    "向BOSS发送消息",
    "发送消息",
]

BOSS_STAY_BUTTON_KEYWORDS = ["留在此页", "留在"]
BOSS_CONTINUE_CHAT_KEYWORDS = ["继续沟通"]


def load_dotenv(path):
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8-sig", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def env_first(*names, default=""):
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return default


def build_proxy_map():
    proxy = env_first("VISION_PROXY", "MIMO_PROXY", "HTTPS_PROXY", "HTTP_PROXY", "ALL_PROXY")
    if not proxy:
        proxy_host = env_first("PROXY_HOST")
        proxy_port = env_first("PROXY_PORT")
        if proxy_host and proxy_port:
            proxy = "http://{}:{}".format(proxy_host, proxy_port)
    if not proxy:
        return None
    return {"http": proxy, "https": proxy}


def masked(value):
    if not value:
        return ""
    if len(value) <= 12:
        return value[:2] + "***"
    return value[:8] + "***" + value[-4:]


def emit_final(result, exit_code=0):
    print(json.dumps(result, ensure_ascii=False))
    sys.exit(exit_code)


def capture_screen():
    SCREENSHOT_DIR.mkdir(exist_ok=True)
    image = pyautogui.screenshot()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    path = SCREENSHOT_DIR / f"mimo_ocr_{timestamp}.png"
    image.save(path)
    return image, path


def image_to_data_url(image, max_width=1280):
    width, height = image.size
    if width > max_width:
        ratio = max_width / float(width)
        image = image.resize((max_width, int(height * ratio)))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return "data:image/png;base64," + encoded


def get_ocr_reader():
    try:
        import easyocr
    except Exception as exc:
        raise RuntimeError("easyocr is not available: " + str(exc))

    model_dir = env_first("EASYOCR_MODEL_DIR", "OCR_MODEL_DIR")
    kwargs = {"gpu": False}
    if model_dir:
        kwargs["model_storage_directory"] = model_dir
    return easyocr.Reader(["ch_sim", "en"], **kwargs)


def run_ocr(reader, image_path):
    import numpy as np
    from PIL import Image

    image = np.array(Image.open(image_path).convert("RGB"))
    raw_results = reader.readtext(image)
    elements = []
    for bbox, text, confidence in raw_results:
        if confidence < 0.25:
            continue
        x = int((bbox[0][0] + bbox[2][0]) / 2)
        y = int((bbox[0][1] + bbox[2][1]) / 2)
        elements.append(
            {
                "text": text,
                "x": x,
                "y": y,
                "confidence": round(float(confidence), 3),
            }
        )
    return elements


def contains_any(text, keywords):
    lower = text.lower()
    return any(keyword.lower() in lower for keyword in keywords)


def screen_text(elements):
    return " ".join(element.get("text", "") for element in elements)


def is_blocked(elements):
    return contains_any(screen_text(elements), BLOCKING_KEYWORDS)


def success_detected(elements):
    return contains_any(screen_text(elements), SUCCESS_KEYWORDS)


def boss_success_dialog_detected(elements):
    text = screen_text(elements)
    has_sent = contains_any(text, BOSS_SUCCESS_DIALOG_KEYWORDS)
    has_dialog_actions = contains_any(text, BOSS_STAY_BUTTON_KEYWORDS + BOSS_CONTINUE_CHAT_KEYWORDS)
    return has_sent and (has_dialog_actions or "Boss您好" in text or "BOSS您好" in text)


def find_ocr_point(elements, keywords):
    for element in elements:
        text = str(element.get("text", ""))
        if any(keyword.lower() in text.lower() for keyword in keywords):
            x = element.get("x")
            y = element.get("y")
            if x is not None and y is not None:
                return int(x), int(y), text
    return None


def dismiss_boss_success_dialog(elements, args):
    if args.dry_run:
        return "dry_run"
    target = find_ocr_point(elements, BOSS_STAY_BUTTON_KEYWORDS)
    if target:
        x, y, text = target
        pyautogui.click(x, y)
        time.sleep(args.action_delay)
        return "clicked_" + text
    continue_target = find_ocr_point(elements, BOSS_CONTINUE_CHAT_KEYWORDS)
    if continue_target:
        x, y, text = continue_target
        width, _height = pyautogui.size()
        offset = min(max(int(width * 0.055), 80), 150)
        pyautogui.click(max(1, x - offset), y)
        time.sleep(args.action_delay)
        return "clicked_left_of_" + text
    pyautogui.press("esc")
    time.sleep(args.action_delay)
    return "pressed_esc_no_stay_button"


def boss_continue_chat_decision(decision, args):
    if args.platform != "boss":
        return False
    joined = " ".join(str(decision.get(name, "") or "") for name in ("text", "target_text", "reason", "expect", "value"))
    return contains_any(joined, BOSS_CONTINUE_CHAT_KEYWORDS)


def likely_final_submit(decision):
    joined = " ".join(
        str(decision.get(name, ""))
        for name in ("text", "target_text", "reason", "expect")
    )
    return contains_any(joined, FINAL_SUBMIT_KEYWORDS)


def compact_elements(elements, limit=80):
    return elements[:limit]


def build_prompt(args, elements, step, delivered):
    payload = {
        "objective": args.objective,
        "platform": args.platform,
        "keyword": args.keyword,
        "target_count": args.count,
        "delivered_so_far": delivered,
        "step": step,
        "screen_size": {"width": pyautogui.size().width, "height": pyautogui.size().height},
        "ocr_elements": compact_elements(elements),
        "allowed_actions": [
            "click",
            "scroll",
            "type",
            "press",
            "hotkey",
            "wait",
            "done",
            "need_user",
        ],
        "rules": [
            "Return one JSON object only. No markdown.",
            "The action field is required. Never return null, None, empty string, or an unsupported action; use wait or need_user if unsure.",
            "Use actual screen coordinates from OCR elements when clicking.",
            "If captcha, slider, SMS code, QR login, login page, or security check is visible, choose need_user.",
            "If final application submit/apply/send-resume is needed, set is_final_submit=true.",
            "On BOSS, if a dialog says 已向BOSS发送消息 and shows 留在此页 / 继续沟通, the job is already delivered. Click 留在此页 only. Never click 继续沟通.",
            "Do not invent success. Use done only when the current job is already applied or the objective is complete.",
        ],
        "json_schema": {
            "action": "click|scroll|type|press|hotkey|wait|done|need_user",
            "x": "integer, required for click",
            "y": "integer, required for click",
            "text": "visible target text if any",
            "value": "text to type, or key name, or hotkey list",
            "direction": "up|down for scroll",
            "is_final_submit": "boolean",
            "reason": "short reason",
            "expect": "what should change after the action",
        },
    }
    return (
        "You are controlling the user's own desktop browser to help with a job application.\n"
        "Make a single safe next-step decision from OCR text and screenshot.\n"
        + json.dumps(payload, ensure_ascii=False)
    )


def call_mimo(prompt, image):
    api_key = env_first("VISION_API_KEY", "MIMO_API_KEY", "OPENAI_API_KEY")
    base_url = env_first(
        "VISION_BASE_URL",
        "MIMO_BASE_URL",
        "OPENAI_BASE_URL",
        default="https://token-plan-sgp.xiaomimimo.com/v1",
    )
    model = env_first("VISION_MODEL", "MIMO_MODEL", default="mimo-v2.5")
    if not api_key:
        raise RuntimeError("Missing VISION_API_KEY, MIMO_API_KEY, or OPENAI_API_KEY")

    endpoint = base_url.rstrip("/") + "/chat/completions"
    body = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": image_to_data_url(image)}},
                ],
            }
        ],
        "max_tokens": 2000,
        "temperature": 0.1,
    }
    proxy_map = build_proxy_map()
    request_kwargs = {
        "headers": {
            "Authorization": "Bearer " + api_key,
            "Content-Type": "application/json",
        },
        "json": body,
        "timeout": 45,
    }
    if proxy_map:
        request_kwargs["proxies"] = proxy_map
    if certifi:
        request_kwargs["verify"] = certifi.where()

    try:
        response = requests.post(endpoint, **request_kwargs)
        raw = response.text
        response.raise_for_status()
    except requests.HTTPError as exc:
        detail = exc.response.text if exc.response is not None else str(exc)
        status_code = exc.response.status_code if exc.response is not None else "unknown"
        raise RuntimeError("Vision model HTTP error {}: {}".format(status_code, detail[:500]))
    except requests.RequestException as exc:
        proxy = proxy_map.get("https") if proxy_map else ""
        raise RuntimeError(
            "Vision model request failed: {}; endpoint={}; proxy={}".format(
                exc,
                endpoint,
                masked(proxy),
            )
        )

    parsed = json.loads(raw)
    message = parsed["choices"][0].get("message", {})
    return message.get("content") or message.get("reasoning_content") or ""


def parse_decision(raw):
    # Find first complete JSON object (non-greedy)
    match = re.search(r"\{[^{}]*\}", raw)
    if not match:
        # Try nested JSON (one level)
        match = re.search(r"\{.*?\}", raw, re.DOTALL)
    if not match:
        raise ValueError("Mimo did not return a JSON object: " + raw[:300])
    decision = json.loads(match.group(0))
    original_action = decision.get("action")
    action = str(original_action or "").lower().strip()
    action_aliases = {
        "tap": "click",
        "select": "click",
        "noop": "wait",
        "no_op": "wait",
        "none": "wait",
        "null": "wait",
        "": "wait",
        "back": "hotkey",
    }
    action = action_aliases.get(action, action)
    if action == "hotkey" and str(original_action or "").lower().strip() == "back" and not decision.get("value"):
        decision["value"] = ["alt", "left"]
    allowed = {"click", "scroll", "type", "press", "hotkey", "wait", "done", "need_user"}
    if action not in allowed:
        decision.setdefault("reason", "unsupported vision action: " + str(original_action))
        action = "need_user"
    if action == "wait" and (original_action is None or str(original_action).lower().strip() in {"", "none", "null", "noop", "no_op"}):
        decision.setdefault("reason", "vision model omitted action; waiting for a fresh screenshot")
    decision["action"] = action
    return decision


def execute_decision(decision, args):
    action = decision["action"]
    if action in {"done", "need_user"}:
        return action

    if boss_continue_chat_decision(decision, args):
        return "blocked_boss_continue_chat"

    if decision.get("is_final_submit") or likely_final_submit(decision):
        if not args.auto_submit:
            return "need_user_final_submit"

    if args.dry_run:
        return "dry_run"

    if action == "click":
        x = int(decision.get("x", -1))
        y = int(decision.get("y", -1))
        width, height = pyautogui.size()
        if x < 0 or y < 0 or x > width or y > height:
            return "invalid_coordinates"
        pyautogui.click(x, y)
    elif action == "scroll":
        direction = str(decision.get("direction", "down")).lower()
        amount = 5 if direction == "up" else -5
        pyautogui.scroll(amount)
    elif action == "type":
        value = str(decision.get("value", ""))
        if value:
            try:
                import pyperclip

                pyperclip.copy(value)
                pyautogui.hotkey("ctrl", "v")
            except Exception:
                pyautogui.write(value, interval=0.03)
    elif action == "press":
        value = str(decision.get("value", ""))
        if value:
            pyautogui.press(value)
    elif action == "hotkey":
        value = decision.get("value", [])
        if isinstance(value, str):
            value = [part.strip() for part in value.split("+") if part.strip()]
        if value:
            pyautogui.hotkey(*value)
    elif action == "wait":
        pass

    time.sleep(args.action_delay)
    return "executed"


def normalize_text(value):
    return str(value or "").lower()


def window_title(window):
    try:
        return str(getattr(window, "title", "") or "")
    except Exception:
        return ""


def all_desktop_windows():
    try:
        return [window for window in pyautogui.getAllWindows() if window_title(window).strip()]
    except Exception:
        return []


def title_matches(title, keywords):
    lowered = normalize_text(title)
    return any(normalize_text(keyword) in lowered for keyword in keywords)


def activate_window(window):
    try:
        if getattr(window, "isMinimized", False):
            window.restore()
        window.activate()
        time.sleep(0.8)
        return True
    except Exception:
        try:
            window.maximize()
            window.activate()
            time.sleep(0.8)
            return True
        except Exception:
            pass

    try:
        left = int(getattr(window, "left", 0) or 0)
        top = int(getattr(window, "top", 0) or 0)
        width = int(getattr(window, "width", 0) or 0)
        if width > 0:
            pyautogui.click(left + min(120, max(20, width // 3)), top + 16)
            time.sleep(0.8)
            return True
    except Exception:
        pass
    return False


def focus_platform_window(platform, allow_browser_fallback=False):
    windows = all_desktop_windows()
    platform_keywords = PLATFORM_WINDOW_KEYWORDS.get(platform, [])
    matched_title = ""
    for window in windows:
        title = window_title(window)
        if title_matches(title, platform_keywords):
            matched_title = title
            if activate_window(window):
                return True, title

    if allow_browser_fallback:
        for window in windows:
            title = window_title(window)
            if title_matches(title, BROWSER_WINDOW_KEYWORDS):
                matched_title = title
                if activate_window(window):
                    return True, title

    return False, matched_title


def open_platform(args):
    if args.no_open:
        return
    url_template = PLATFORM_URLS.get(args.platform)
    if not url_template:
        return
    webbrowser.open(url_template.format(keyword=args.keyword))
    time.sleep(args.initial_delay)
    focus_platform_window(args.platform, allow_browser_fallback=True)


def run_agent(args):
    load_dotenv(ROOT / ".env")
    result = {
        "success": False,
        "platform": args.platform,
        "keyword": args.keyword,
        "attempted": args.count,
        "delivered": 0,
        "skipped": 0,
        "needsUserAction": False,
        "error": None,
        "duration": 0,
        "timestamp": datetime.now().isoformat(),
        "events": [],
    }
    start_time = time.time()

    try:
        reader = get_ocr_reader()
        open_platform(args)

        for job_index in range(args.count):
            job_delivered = False
            for step in range(args.max_steps):
                focused, focused_title = focus_platform_window(args.platform)
                if not focused:
                    result["needsUserAction"] = True
                    result["events"].append(
                        {
                            "job": job_index + 1,
                            "step": step + 1,
                            "action": "need_user",
                            "reason": "target_browser_not_focused",
                            "expect": "Open or focus the target job-search browser tab, then retry.",
                        }
                    )
                    break
                image, image_path = capture_screen()
                elements = run_ocr(reader, image_path)
                visible_text = screen_text(elements)

                if is_blocked(elements):
                    result["needsUserAction"] = True
                    result["events"].append(
                        {"job": job_index + 1, "step": step + 1, "action": "need_user", "reason": "blocked_state"}
                    )
                    break

                if args.platform == "boss" and (
                    boss_success_dialog_detected(elements)
                    or contains_any(visible_text, BOSS_SUCCESS_DIALOG_KEYWORDS)
                ):
                    result["delivered"] += 1
                    job_delivered = True
                    dismiss_outcome = dismiss_boss_success_dialog(elements, args)
                    result["events"].append(
                        {
                            "job": job_index + 1,
                            "step": step + 1,
                            "action": "boss_success_dialog_detected",
                            "outcome": dismiss_outcome,
                        }
                    )
                    break

                if success_detected(elements):
                    result["delivered"] += 1
                    job_delivered = True
                    result["events"].append(
                        {"job": job_index + 1, "step": step + 1, "action": "success_detected"}
                    )
                    if not args.dry_run:
                        pyautogui.press("esc")
                        time.sleep(1)
                    break

                prompt = build_prompt(args, elements, step + 1, result["delivered"])
                raw_decision = call_mimo(prompt, image)
                decision = parse_decision(raw_decision)
                outcome = execute_decision(decision, args)

                event = {
                    "job": job_index + 1,
                    "step": step + 1,
                    "action": decision.get("action"),
                    "outcome": outcome,
                    "text": decision.get("text"),
                    "x": decision.get("x"),
                    "y": decision.get("y"),
                    "reason": decision.get("reason"),
                    "windowTitle": focused_title,
                    "screenshot": str(image_path),
                    "visibleTextSample": visible_text[:300],
                }
                result["events"].append(event)

                if outcome.startswith("need_user") or decision["action"] == "need_user":
                    result["needsUserAction"] = True
                    break
                if decision["action"] == "done":
                    break

            if result["needsUserAction"]:
                break
            if not job_delivered:
                result["skipped"] += 1
            if job_index < args.count - 1 and not args.dry_run:
                pyautogui.scroll(-5)
                time.sleep(args.action_delay)

        result["success"] = result["delivered"] > 0 and not result["needsUserAction"]
        result["duration"] = round(time.time() - start_time, 2)
        emit_final(result, 0 if result["success"] or result["needsUserAction"] else 1)
    except Exception as exc:
        result["error"] = str(exc)
        result["duration"] = round(time.time() - start_time, 2)
        emit_final(result, 2)


def parse_args():
    parser = argparse.ArgumentParser(description="Mimo OCR job application agent")
    parser.add_argument("--platform", required=True, choices=sorted(PLATFORM_URLS.keys()))
    parser.add_argument("--keyword", required=True)
    parser.add_argument("--count", type=int, default=1)
    parser.add_argument("--objective", default="")
    parser.add_argument("--max-steps", type=int, default=12)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--auto-submit", action="store_true")
    parser.add_argument("--no-open", action="store_true")
    parser.add_argument("--initial-delay", type=float, default=6.0)
    parser.add_argument("--action-delay", type=float, default=2.0)
    args = parser.parse_args()
    if not args.objective:
        args.objective = (
            "Find a suitable {keyword} job on {platform}, open one job, "
            "and proceed with the application flow."
        ).format(keyword=args.keyword, platform=args.platform)
    return args


if __name__ == "__main__":
    run_agent(parse_args())
