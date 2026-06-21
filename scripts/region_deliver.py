# -*- coding: utf-8 -*-
"""
AI投递 - 使用AI识别+固定偏移
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
            max_tokens=200
        )
        content = resp.choices[0].message.content
        reasoning = resp.choices[0].message.reasoning_content
        return content if content else reasoning
    except Exception as e:
        return str(e)


def find_element_by_text(text_to_find):
    """通过文字找位置"""
    img = take_screenshot()
    prompt = f'在截图中找到"{text_to_find}"，它在屏幕的什么区域？回复：上/中/下/左/右'
    result = ai_analyze(img, prompt)
    return result


def click_by_region(region):
    """根据区域点击"""
    # 屏幕划分为9宫格
    positions = {
        '左上': (200, 112),
        '上': (400, 112),
        '右上': (600, 112),
        '左': (200, 225),
        '中': (400, 225),
        '右': (600, 225),
        '左下': (200, 337),
        '下': (400, 337),
        '右下': (600, 337),
    }
    
    for key, pos in positions.items():
        if key in region:
            return pos
    
    return (400, 225)  # 默认中间


print('=== AI Region Delivery ===')

# Step 1: 找职位
print('\n[1] Finding job...')
region = find_element_by_text('Java')
print(f'  Region: {region}')

x, y = click_by_region(region)
print(f'  Clicking at ({x}, {y})...')
pyautogui.click(x, y)
time.sleep(3)

# Step 2: 检查页面
print('\n[2] Checking page...')
img = take_screenshot()
status = ai_analyze(img, '当前是职位列表页还是详情页？有没有投递按钮？')
print(f'  Status: {status}')

# Step 3: 找投递按钮
print('\n[3] Finding apply button...')
region = find_element_by_text('投递简历')
print(f'  Region: {region}')

x, y = click_by_region(region)
print(f'  Clicking at ({x}, {y})...')
pyautogui.click(x, y)
time.sleep(3)

# Step 4: 检查结果
print('\n[4] Checking result...')
img = take_screenshot()
result = ai_analyze(img, '是否投递成功？')
print(f'  Result: {result}')

print('\n=== Done ===')
