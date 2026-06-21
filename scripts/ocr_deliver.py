# -*- coding: utf-8 -*-
"""
使用OCR精确定位职位卡片并投递
"""
import pyautogui
import base64
import openai
import json
import time
import easyocr

API_KEY = 'your_mimo_api_key_here'
BASE_URL = 'https://token-plan-sgp.xiaomimimo.com/v1'

# 初始化OCR
reader = easyocr.Reader(['ch_sim', 'en'], gpu=False)


def take_screenshot():
    screenshot = pyautogui.screenshot()
    screenshot.save('temp.png')
    return 'temp.png'


def ocr_detect(image_path):
    """使用OCR检测文字和位置"""
    results = reader.readtext(image_path)
    detected = []
    for (bbox, text, prob) in results:
        # bbox是四个角的坐标，取中心点
        x = (bbox[0][0] + bbox[2][0]) / 2
        y = (bbox[0][1] + bbox[2][1]) / 2
        detected.append({
            'text': text,
            'x': int(x),
            'y': int(y),
            'confidence': prob
        })
    return detected


def find_java_job(detected):
    """找到Java相关的职位"""
    jobs = []
    for item in detected:
        text = item['text'].lower()
        if 'java' in text and ('开发' in text or '工程师' in text or '实习' in text):
            jobs.append(item)
    return jobs


def find_apply_button(detected):
    """找到投递按钮"""
    keywords = ['投递简历', '立即沟通', '申请职位', '投递', '沟通']
    for item in detected:
        for kw in keywords:
            if kw in item['text']:
                return item
    return None


def find_applied_status(detected):
    """检查是否已投递"""
    keywords = ['已投递', '投递成功', '已沟通', '已申请']
    for item in detected:
        for kw in keywords:
            if kw in item['text']:
                return True
    return False


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
            max_tokens=300
        )
        content = resp.choices[0].message.content
        reasoning = resp.choices[0].message.reasoning_content
        return content if content else reasoning
    except Exception as e:
        return str(e)


def deliver_one():
    """投递一个职位"""
    print('\n=== Start Delivery ===')

    # Step 1: OCR detect jobs
    print('\n[1] OCR detecting jobs...')
    img_path = take_screenshot()
    detected = ocr_detect(img_path)
    print(f'  Found {len(detected)} text elements')

    # Step 2: Find Java job
    print('\n[2] Finding Java job...')
    jobs = find_java_job(detected)
    if not jobs:
        print('  No Java job found')
        return False

    job = jobs[0]
    print(f'  Found: {job["text"]}')
    print(f'  Position: ({job["x"]}, {job["y"]})')

    # Step 3: Click job
    print('\n[3] Clicking job...')
    pyautogui.click(job['x'], job['y'])
    time.sleep(3)

    # Step 4: OCR detect apply button
    print('\n[4] Finding apply button...')
    img_path = take_screenshot()
    detected = ocr_detect(img_path)

    # Check if we're on job detail page
    apply_btn = find_apply_button(detected)
    if not apply_btn:
        print('  No apply button found, clicking job again...')
        # Try clicking more precisely
        pyautogui.click(job['x'], job['y'])
        time.sleep(3)
        img_path = take_screenshot()
        detected = ocr_detect(img_path)
        apply_btn = find_apply_button(detected)

    if not apply_btn:
        print('  Still no apply button found')
        pyautogui.hotkey('alt', 'left')
        time.sleep(2)
        return False

    print(f'  Found: {apply_btn["text"]}')
    print(f'  Position: ({apply_btn["x"]}, {apply_btn["y"]})')

    # Step 5: Click apply
    print('\n[5] Clicking apply...')
    pyautogui.click(apply_btn['x'], apply_btn['y'])
    time.sleep(3)

    # Step 6: Check result
    print('\n[6] Checking result...')
    img_path = take_screenshot()
    detected = ocr_detect(img_path)

    if find_applied_status(detected):
        print('  [SUCCESS] Applied!')
        pyautogui.press('esc')
        time.sleep(1)
        pyautogui.hotkey('alt', 'left')
        time.sleep(2)
        return True

    # Use AI to double check
    with open(img_path, 'rb') as f:
        img_b64 = base64.b64encode(f.read()).decode()
    result = ai_analyze(img_b64, '是否投递成功？有没有"已投递"等提示？')
    print(f'  AI check: {result}')

    pyautogui.press('esc')
    time.sleep(1)
    pyautogui.hotkey('alt', 'left')
    time.sleep(2)
    return False


if __name__ == '__main__':
    print('=== OCR Delivery Test ===')
    success = deliver_one()
    print(f'\nResult: {"SUCCESS" if success else "FAILED"}')
