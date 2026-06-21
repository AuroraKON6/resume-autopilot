# -*- coding: utf-8 -*-
import pyautogui
import base64
import openai
import json
import time
import os
from datetime import datetime

API_KEY = 'your_mimo_api_key_here'
BASE_URL = 'https://token-plan-sgp.xiaomimimo.com/v1'
MODEL = 'mimo-v2.5'


def take_screenshot():
    screenshot = pyautogui.screenshot()
    screenshot = screenshot.resize((800, 450))
    screenshot.save('temp.png', quality=60)
    with open('temp.png', 'rb') as f:
        return base64.b64encode(f.read()).decode()


def ai_analyze(img_b64, prompt):
    client = openai.OpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=30)
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{'role': 'user', 'content': [
                {'type': 'text', 'text': prompt},
                {'type': 'image_url', 'image_url': {'url': f'data:image/png;base64,{img_b64}'}}
            ]}],
            max_tokens=500
        )
        content = resp.choices[0].message.content
        reasoning = resp.choices[0].message.reasoning_content
        return content if content else reasoning
    except Exception as e:
        print(f'AI error: {e}')
        return None


def parse_json(text):
    if not text:
        return None
    try:
        start = text.find('{')
        end = text.rfind('}') + 1
        if start >= 0 and end > start:
            return json.loads(text[start:end])
    except:
        pass
    return None


def find_first_job():
    img = take_screenshot()
    prompt = '请分析这个招聘网站截图，找到第一个职位卡片的位置。用JSON格式回复：{"found":true,"x":点击x坐标,"y":点击y坐标,"title":"职位名称"}。如果没找到返回{"found":false}'
    result = ai_analyze(img, prompt)
    return parse_json(result)


def find_apply_button():
    img = take_screenshot()
    prompt = '请分析这个截图，找到"投递简历"、"立即沟通"、"申请职位"或类似的按钮。用JSON格式回复：{"found":true,"x":按钮x坐标,"y":按钮y坐标,"text":"按钮文字"}。如果没找到返回{"found":false}'
    result = ai_analyze(img, prompt)
    return parse_json(result)


def check_applied():
    img = take_screenshot()
    prompt = '请分析这个截图，判断是否已经投递成功。投递成功的标志："已投递"、"投递成功"、"已沟通"、按钮变灰等。用JSON格式回复：{"applied":true,"reason":"成功原因"}。如果没成功返回{"applied":false,"reason":"失败原因"}'
    result = ai_analyze(img, prompt)
    return parse_json(result)


def deliver_one():
    """投递一个职位的完整流程"""
    print('\n[1] Finding job...')
    job = find_first_job()
    if not job or not job.get('found'):
        print('  No job found')
        return False

    print(f'  Found: {job.get("title")}')
    print(f'  Position: ({job.get("x")}, {job.get("y")})')

    print('\n[2] Clicking job...')
    pyautogui.click(job['x'], job['y'])
    time.sleep(3)

    print('\n[3] Finding apply button...')
    btn = find_apply_button()
    if not btn or not btn.get('found'):
        print('  No apply button found')
        pyautogui.hotkey('alt', 'left')
        time.sleep(2)
        return False

    print(f'  Found: {btn.get("text")}')
    print(f'  Position: ({btn.get("x")}, {btn.get("y")})')

    print('\n[4] Clicking apply...')
    pyautogui.click(btn['x'], btn['y'])
    time.sleep(3)

    print('\n[5] Checking result...')
    result = check_applied()
    if result and result.get('applied'):
        print(f'  [SUCCESS] {result.get("reason")}')
        pyautogui.press('esc')
        time.sleep(1)
        pyautogui.hotkey('alt', 'left')
        time.sleep(2)
        return True
    else:
        print(f'  [NOT CONFIRMED] {result.get("reason", "unknown")}')
        pyautogui.press('esc')
        time.sleep(1)
        pyautogui.hotkey('alt', 'left')
        time.sleep(2)
        return False


if __name__ == '__main__':
    print('=== AI Delivery Test ===')
    success = deliver_one()
    print(f'\nResult: {"SUCCESS" if success else "FAILED"}')
