# -*- coding: utf-8 -*-
"""
使用OCR精确定位职位并投递
"""
import pyautogui
import easyocr
import time
import json

print('Loading OCR...')
reader = easyocr.Reader(['ch_sim', 'en'], gpu=False,
                        model_storage_directory='C:/Users/K-ON的学习本/.EasyOCR/model')


def find_java_job():
    """找到Java相关职位"""
    screenshot = pyautogui.screenshot()
    screenshot.save('ocr_screen.png')

    results = reader.readtext('ocr_screen.png')
    jobs = []

    for bbox, text, prob in results:
        text_lower = text.lower()
        # 找Java相关职位
        if 'java' in text_lower and ('开发' in text or '工程师' in text or '实习' in text or '|' in text):
            x = int((bbox[0][0] + bbox[2][0]) / 2)
            y = int((bbox[0][1] + bbox[2][1]) / 2)
            jobs.append({'text': text, 'x': x, 'y': y, 'conf': prob})

    return jobs


def find_apply_button():
    """找到投递按钮"""
    screenshot = pyautogui.screenshot()
    screenshot.save('ocr_screen.png')

    results = reader.readtext('ocr_screen.png')
    buttons = []

    keywords = ['投递简历', '立即沟通', '申请职位', '投递', '沟通', '申请', '立即', '发送简历', '投递']

    for bbox, text, prob in results:
        for kw in keywords:
            if kw in text:
                x = int((bbox[0][0] + bbox[2][0]) / 2)
                y = int((bbox[0][1] + bbox[2][1]) / 2)
                buttons.append({'text': text, 'x': x, 'y': y, 'conf': prob})
                break

    return buttons


def check_applied():
    """检查是否已投递"""
    screenshot = pyautogui.screenshot()
    screenshot.save('ocr_screen.png')

    results = reader.readtext('ocr_screen.png')

    keywords = ['已投递', '投递成功', '已沟通', '已申请', '已发送']

    for bbox, text, prob in results:
        for kw in keywords:
            if kw in text:
                return True

    return False


def deliver_one():
    """投递一个职位"""
    print('\n=== OCR Delivery ===')

    # Step 1: Find Java job
    print('\n[1] Finding Java job...')
    jobs = find_java_job()

    if not jobs:
        print('  No Java job found')
        print('  Make sure browser is open with job listings')
        return False

    job = jobs[0]
    print(f'  Found: "{job["text"]}"')
    print(f'  Position: ({job["x"]}, {job["y"]})')

    # Step 2: Click job
    print('\n[2] Clicking job...')
    pyautogui.click(job['x'], job['y'])
    time.sleep(4)  # Wait for page load

    # Step 3: Scroll down to find apply button
    print('\n[3] Scrolling to find apply button...')
    for i in range(3):
        pyautogui.scroll(-300)
        time.sleep(1)

    # Step 4: Find apply button
    print('\n[4] Finding apply button...')
    buttons = find_apply_button()

    if not buttons:
        print('  No apply button found, trying to scroll more...')
        for i in range(2):
            pyautogui.scroll(-300)
            time.sleep(1)
        buttons = find_apply_button()

    if not buttons:
        print('  Still no apply button found')
        # Try clicking at typical button positions
        print('  Trying default button position (2100, 500)...')
        pyautogui.click(2100, 500)
        time.sleep(3)

        if check_applied():
            print('  [SUCCESS] Applied at default position!')
            pyautogui.press('esc')
            time.sleep(1)
            pyautogui.hotkey('alt', 'left')
            time.sleep(2)
            return True

        pyautogui.hotkey('alt', 'left')
        time.sleep(2)
        return False

    btn = buttons[0]
    print(f'  Found: "{btn["text"]}"')
    print(f'  Position: ({btn["x"]}, {btn["y"]})')

    # Step 5: Click apply
    print('\n[5] Clicking apply...')
    pyautogui.click(btn['x'], btn['y'])
    time.sleep(3)

    # Step 6: Check result
    print('\n[6] Checking result...')
    if check_applied():
        print('  [SUCCESS] Applied!')
        pyautogui.press('esc')
        time.sleep(1)
        pyautogui.hotkey('alt', 'left')
        time.sleep(2)
        return True
    else:
        print('  [NOT CONFIRMED]')
        pyautogui.press('esc')
        time.sleep(1)
        pyautogui.hotkey('alt', 'left')
        time.sleep(2)
        return False


if __name__ == '__main__':
    # First scan the screen
    print('=== Scanning current screen ===')
    screenshot = pyautogui.screenshot()
    screenshot.save('ocr_screen.png')
    results = reader.readtext('ocr_screen.png')

    print(f'\nFound {len(results)} text elements:')
    for i, (bbox, text, prob) in enumerate(results[:20]):
        x = int((bbox[0][0] + bbox[2][0]) / 2)
        y = int((bbox[0][1] + bbox[2][1]) / 2)
        print(f'  [{i}] ({x}, {y}) "{text}" conf={prob:.2f}')

    # Then try to deliver
    print('\n\n=== Starting delivery ===')
    success = deliver_one()
    print(f'\nResult: {"SUCCESS" if success else "FAILED"}')
