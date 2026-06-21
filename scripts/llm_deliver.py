# -*- coding: utf-8 -*-
"""
LLM驱动的智能投递 - AI分析屏幕，AI决定操作
"""
import pyautogui
import base64
import openai
import json
import time
import sys

API_KEY = 'your_mimo_api_key_here'
BASE_URL = 'https://token-plan-sgp.xiaomimimo.com/v1'
MODEL = 'mimo-v2.5'


def screenshot_base64():
    """截图并转base64"""
    screenshot = pyautogui.screenshot()
    screenshot = screenshot.resize((800, 450))
    screenshot.save('screen.png', quality=60)
    with open('screen.png', 'rb') as f:
        return base64.b64encode(f.read()).decode()


def ask_ai(image_b64, question):
    """问AI"""
    client = openai.OpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=30)
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{
                'role': 'user',
                'content': [
                    {'type': 'text', 'text': question},
                    {'type': 'image_url', 'image_url': {'url': f'data:image/png;base64,{image_b64}'}}
                ]
            }],
            max_tokens=500
        )
        content = resp.choices[0].message.content
        reasoning = resp.choices[0].message.reasoning_content
        # mimo模型响应在reasoning中
        return content if content else reasoning
    except Exception as e:
        return str(e)


def ai_decide(image_b64):
    """让AI决定下一步操作"""
    prompt = """看截图，找"投递"按钮位置。屏幕800x450。

只回复JSON：
{"action":"click_apply","x":数字,"y":数字}"""

    result = ask_ai(image_b64, prompt)
    
    if not result:
        return None
    
    # 解析JSON
    try:
        start = result.find('{')
        end = result.rfind('}') + 1
        if start >= 0 and end > start:
            data = json.loads(result[start:end])
            x = data.get('x', 0)
            y = data.get('y', 0)
            if 0 <= x <= 800 and 0 <= y <= 450:
                return data
    except:
        pass
    
    # 如果JSON解析失败，尝试从文本中提取坐标
    import re
    # 找 "投递" 按钮附近的坐标
    match = re.search(r'投递.*?\((\d+),\s*(\d+)\)', result)
    if match:
        x, y = int(match.group(1)), int(match.group(2))
        if 0 <= x <= 800 and 0 <= y <= 450:
            return {'action': 'click_apply', 'x': x, 'y': y}
    
    # 找任何坐标
    match = re.search(r'\((\d+),\s*(\d+)\)', result)
    if match:
        x, y = int(match.group(1)), int(match.group(2))
        if 0 <= x <= 800 and 0 <= y <= 450:
            return {'action': 'click_apply', 'x': x, 'y': y}
    
    return None


def deliver_one():
    """投递一个职位"""
    print('\n--- AI Deliver One ---')
    
    for attempt in range(5):
        print(f'\n[Attempt {attempt+1}] AI analyzing...')
        
        img = screenshot_base64()
        decision = ai_decide(img)
        
        if not decision:
            print('  AI returned no decision, retrying...')
            time.sleep(2)
            continue
        
        action = decision.get('action')
        x = decision.get('x', 0)
        y = decision.get('y', 0)
        reason = decision.get('reason', '')
        
        print(f'  AI says: {action}')
        print(f'  Position: ({x}, {y})')
        print(f'  Reason: {reason}')
        
        if action == 'click_apply':
            print(f'  [ACTION] Clicking apply at ({x}, {y})')
            pyautogui.click(x, y)
            time.sleep(3)
            
            # 检查是否成功
            img = screenshot_base64()
            check = ask_ai(img, '是否投递成功？回复：成功 或 未成功')
            print(f'  AI check: {check}')
            
            if '成功' in check and '未' not in check:
                print('  [SUCCESS] Confirmed!')
                pyautogui.press('esc')
                time.sleep(1)
                return True
            else:
                print('  [NOT CONFIRMED]')
                pyautogui.press('esc')
                time.sleep(1)
        
        elif action == 'close_popup':
            print('  [ACTION] Closing popup')
            pyautogui.press('esc')
            time.sleep(1)
            return True
        
        elif action == 'scroll':
            print('  [ACTION] Scrolling')
            pyautogui.scroll(-300)
            time.sleep(2)
        
        elif action == 'click_job':
            print(f'  [ACTION] Clicking job at ({x}, {y})')
            pyautogui.click(x, y)
            time.sleep(3)
        
        elif action == 'done':
            print('  [DONE] No more jobs')
            return False
        
        else:
            print(f'  [UNKNOWN] {action}')
            time.sleep(2)
    
    return False


def deliver_batch(count):
    """批量投递"""
    print('\n' + '='*60)
    print(f'LLM-Driven Delivery: target {count} jobs')
    print('='*60)
    
    delivered = 0
    
    for i in range(count):
        print(f'\n{"="*50}')
        print(f'[Job {i+1}/{count}]')
        print('='*50)
        
        success = deliver_one()
        
        if success:
            delivered += 1
            print(f'\n[SCORE] {delivered}/{count}')
        else:
            print(f'\n[SCORE] Failed, {delivered}/{count}')
        
        if i < count - 1:
            print('\nScrolling for more...')
            pyautogui.scroll(-300)
            time.sleep(2)
    
    print('\n' + '='*60)
    print(f'COMPLETE: {delivered}/{count} delivered')
    print('='*60)
    
    return delivered


if __name__ == '__main__':
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    deliver_batch(count)
