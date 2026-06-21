# -*- coding: utf-8 -*-
import pyautogui
import base64
import openai

API_KEY = 'your_mimo_api_key_here'
BASE_URL = 'https://token-plan-sgp.xiaomimimo.com/v1'

screenshot = pyautogui.screenshot()
screenshot = screenshot.resize((800, 450))
screenshot.save('screen.png', quality=60)
with open('screen.png', 'rb') as f:
    img_b64 = base64.b64encode(f.read()).decode()

client = openai.OpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=30)

prompt = """分析这个截图，决定下一步操作。回复JSON：
{"action":"click_apply","x":数字,"y":数字,"reason":"原因"}"""

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

print('content:', repr(resp.choices[0].message.content))
print('reasoning:', repr(resp.choices[0].message.reasoning_content[:500]) if resp.choices[0].message.reasoning_content else None)
