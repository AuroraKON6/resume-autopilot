# -*- coding: utf-8 -*-
import pyautogui
import base64
import openai
import json
import re

API_KEY = 'your_mimo_api_key_here'
BASE_URL = 'https://token-plan-sgp.xiaomimimo.com/v1'

screenshot = pyautogui.screenshot()
screenshot = screenshot.resize((800, 450))
screenshot.save('temp.png', quality=60)
with open('temp.png', 'rb') as f:
    img_b64 = base64.b64encode(f.read()).decode()

client = openai.OpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=30)

prompt = """看这个截图，第一个职位卡片在屏幕的哪个区域？

回复格式（必须用阿拉伯数字）：
{"found":true,"x":400,"y":300,"title":"Java"}

x范围：0-800
y范围：0-450"""

resp = client.chat.completions.create(
    model='mimo-v2.5',
    messages=[{
        'role': 'user',
        'content': [
            {'type': 'text', 'text': prompt},
            {'type': 'image_url', 'image_url': {'url': f'data:image/png;base64,{img_b64}'}}
        ]
    }],
    max_tokens=300
)

content = resp.choices[0].message.content
reasoning = resp.choices[0].message.reasoning_content
print('content:', repr(content))
print('reasoning:', repr(reasoning[:200]) if reasoning else None)

text = content if content else reasoning
if text:
    # 使用正则提取JSON
    match = re.search(r'\{[^}]+\}', text)
    if match:
        json_str = match.group()
        print('JSON:', json_str)
        try:
            data = json.loads(json_str)
            print('Parsed:', data)
        except Exception as e:
            print('Parse error:', e)
