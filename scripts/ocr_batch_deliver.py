# -*- coding: utf-8 -*-
"""
完整OCR投递脚本 - 实时检测，不记位置
"""
import pyautogui
import easyocr
import time
import json
import os
import sys
from datetime import datetime

print('Loading OCR...')
reader = easyocr.Reader(['ch_sim', 'en'], gpu=False,
                        model_storage_directory='C:/Users/K-ON的学习本/.EasyOCR/model')


def scan_screen():
    """扫描屏幕，返回所有文字和位置"""
    screenshot = pyautogui.screenshot()
    screenshot.save('screen.png')
    return reader.readtext('screen.png')


def find_elements(keywords, exclude=None):
    """找包含关键词的元素"""
    results = scan_screen()
    found = []
    
    for bbox, text, prob in results:
        if prob < 0.3:
            continue
        
        # 排除词
        if exclude:
            skip = False
            for ex in exclude:
                if ex in text:
                    skip = True
                    break
            if skip:
                continue
        
        for kw in keywords:
            if kw in text:
                x = int((bbox[0][0] + bbox[2][0]) / 2)
                y = int((bbox[0][1] + bbox[2][1]) / 2)
                found.append({'text': text, 'x': x, 'y': y, 'conf': prob})
                break
    
    return found


def click_at(x, y, desc=""):
    """点击指定位置"""
    print(f'  Click ({x}, {y}) {desc}')
    pyautogui.click(x, y)


def press_esc():
    """按ESC关闭弹窗"""
    print('  Press ESC')
    pyautogui.press('esc')
    time.sleep(1)


def deliver_one_job():
    """投递一个职位的完整流程"""
    print('\n' + '='*50)
    print('[1] Scanning for apply button...')
    
    # 找投递按钮（排除"投递成功"等）
    apply_btns = find_elements(
        ['投递', '申请职位', '立即沟通'],
        exclude=['成功', '已投递', '已申请']
    )
    
    if not apply_btns:
        print('  No apply button found')
        return False
    
    btn = apply_btns[0]
    print(f'  Found: "{btn["text"]}" at ({btn["x"]}, {btn["y"]})')
    
    # 点击投递
    print('\n[2] Clicking apply...')
    click_at(btn['x'], btn['y'], btn['text'])
    time.sleep(3)
    
    # 检查结果
    print('\n[3] Checking result...')
    success = find_elements(['投递成功', '已投递', '已申请', '成功'])
    
    if success:
        print(f'  [SUCCESS] {success[0]["text"]}')
        
        # 关闭弹窗
        print('\n[4] Closing popup...')
        press_esc()
        
        # 等待页面恢复
        time.sleep(2)
        return True
    else:
        print('  [NOT CONFIRMED]')
        press_esc()
        time.sleep(2)
        return False


def deliver_batch(count):
    """批量投递"""
    print('\n' + '='*60)
    print(f'OCR Batch Delivery: {count} jobs')
    print('='*60)
    
    delivered = 0
    
    for i in range(count):
        print(f'\n--- Job {i+1}/{count} ---')
        
        success = deliver_one_job()
        if success:
            delivered += 1
            print(f'\n[Total] Delivered: {delivered}/{count}')
        else:
            print(f'\n[Total] Failed, delivered: {delivered}/{count}')
        
        # 滚动找更多职位
        if i < count - 1:
            print('\nScrolling...')
            pyautogui.scroll(-300)
            time.sleep(2)
    
    print('\n' + '='*60)
    print(f'DONE: {delivered}/{count} delivered')
    print('='*60)
    
    return delivered


if __name__ == '__main__':
    # 默认投递1个
    count = 1
    if len(sys.argv) > 1:
        count = int(sys.argv[1])
    
    result = deliver_batch(count)
    print(f'\nResult: {result} jobs delivered')
