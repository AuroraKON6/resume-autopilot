# -*- coding: utf-8 -*-
import pyautogui
import base64
import openai
import json
import time

API_KEY = 'your_mimo_api_key_here'
BASE_URL = 'https://token-plan-sgp.xiaomimimo.com/v1'


def take_screenshot():
    screenshot = pyautogui.screenshot()
    screenshot = screenshot.resize((800, 450))
    screenshot.save('temp.png', quality=60)
    with open('temp.png', 'rb') as f:
        return base64.b64encode(f.read()).decode()


def ai_check(img_b64, prompt):
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


print('=== Test AI Delivery Flow ===')

# Step 1: Click on first job (use estimated position)
print('\n[1] Clicking first job at (300, 250)...')
pyautogui.click(300, 250)
time.sleep(3)

# Step 2: Check what page we're on
print('\n[2] Checking current page...')
img = take_screenshot()
result = ai_check(img, '当前页面是什么？是职位详情页吗？有没有"投递简历"或"立即沟通"按钮？')
print(f'  AI: {result}')

# Step 3: Find and click apply button
print('\n[3] Looking for apply button...')
img = take_screenshot()
result = ai_check(img, '"投递简历"或"立即沟通"按钮大概在什么位置？回复格式：{"x":数字,"y":数字}')
print(f'  AI: {result}')

# Try clicking where the button usually is
print('\n[4] Clicking apply button at (700, 400)...')
pyautogui.click(700, 400)
time.sleep(3)

# Step 4: Check if applied
print('\n[5] Checking if applied...')
img = take_screenshot()
result = ai_check(img, '是否已经投递成功？有没有"已投递"、"投递成功"等提示？')
print(f'  AI: {result}')

print('\n=== Test Complete ===')
