# -*- coding: utf-8 -*-
"""
使用AI分析页面布局，然后点击相对位置
"""
import pyautogui
import base64
import openai
import json
import time
import re

API_KEY = 'your_mimo_api_key_here'
BASE_URL = 'https://token-plan-sgp.xiaomimimo.com/v1'


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
            model='mimo-v2.5',
            messages=[{
                'role': 'user',
                'content': [
                    {'type': 'text', 'text': prompt},
                    {'type': 'image_url', 'image_url': {'url': f'data:image/png;base64,{img_b64}'}}
                ]
            }],
            max_tokens=500
        )
        content = resp.choices[0].message.content
        reasoning = resp.choices[0].message.reasoning_content
        return content if content else reasoning
    except Exception as e:
        return str(e)


def get_page_layout():
    """分析页面布局，返回关键区域的相对位置"""
    img = take_screenshot()
    prompt = """分析这个招聘网站截图，告诉我各个区域的位置。

用JSON回复（必须用阿拉伯数字，不要用中文数字）：
{
  "search_box": {"x": 400, "y": 50},
  "first_job": {"x": 400, "y": 200},
  "apply_button": {"x": 700, "y": 400},
  "page_type": "列表页/详情页"
}

屏幕尺寸：800x450像素"""

    result = ai_analyze(img, prompt)
    if result:
        # 尝试提取JSON
        match = re.search(r'\{[^{}]*\{[^{}]*\}[^{}]*\}', result)
        if match:
            try:
                return json.loads(match.group())
            except:
                pass
        # 尝试简单的JSON
        match = re.search(r'\{[^}]+\}', result)
        if match:
            try:
                return json.loads(match.group())
            except:
                pass
    return None


def check_page_status():
    """检查当前页面状态"""
    img = take_screenshot()
    prompt = '当前是什么页面？职位列表页还是职位详情页？有没有"投递简历"按钮？简单回答。'
    return ai_analyze(img, prompt)


def check_applied():
    """检查是否投递成功"""
    img = take_screenshot()
    prompt = '有没有"已投递"、"投递成功"等提示？简单回答有或没有。'
    result = ai_analyze(img, prompt)
    return result and ('有' in result or '成功' in result or '已投递' in result)


print('=== AI Layout Delivery ===')

# Step 1: Get layout
print('\n[1] Analyzing page layout...')
layout = get_page_layout()
print(f'  Layout: {layout}')

if layout:
    # Step 2: Click first job
    job_pos = layout.get('first_job', {})
    x, y = job_pos.get('x', 400), job_pos.get('y', 200)
    print(f'\n[2] Clicking job at ({x}, {y})...')
    pyautogui.click(x, y)
    time.sleep(3)

    # Step 3: Check if on detail page
    print('\n[3] Checking page status...')
    status = check_page_status()
    print(f'  Status: {status}')

    # Step 4: Get new layout for detail page
    print('\n[4] Getting detail page layout...')
    layout2 = get_page_layout()
    print(f'  Layout: {layout2}')

    if layout2:
        # Step 5: Click apply button
        btn_pos = layout2.get('apply_button', {})
        bx, by = btn_pos.get('x', 700), btn_pos.get('y', 400)
        print(f'\n[5] Clicking apply at ({bx}, {by})...')
        pyautogui.click(bx, by)
        time.sleep(3)

        # Step 6: Check result
        print('\n[6] Checking result...')
        if check_applied():
            print('  [SUCCESS] Applied!')
        else:
            print('  [NOT CONFIRMED]')

print('\n=== Done ===')
