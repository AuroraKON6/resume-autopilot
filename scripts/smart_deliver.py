# -*- coding: utf-8 -*-
"""
智能OCR投递 - 实时检测，实时决策
扫描屏幕 -> 判断该做什么 -> 执行 -> 循环
"""
import pyautogui
import easyocr
import time
import sys

print('Loading OCR...')
reader = easyocr.Reader(['ch_sim', 'en'], gpu=False,
                        model_storage_directory='C:/Users/K-ON的学习本/.EasyOCR/model')


def scan():
    """扫描屏幕，返回所有文字"""
    screenshot = pyautogui.screenshot()
    screenshot.save('screen.png')
    results = reader.readtext('screen.png')
    
    elements = []
    for bbox, text, prob in results:
        if prob < 0.3:
            continue
        x = int((bbox[0][0] + bbox[2][0]) / 2)
        y = int((bbox[0][1] + bbox[2][1]) / 2)
        elements.append({'text': text, 'x': x, 'y': y, 'conf': prob})
    
    return elements


def decide(elements):
    """根据屏幕内容决定该做什么"""
    texts = [e['text'] for e in elements]
    full_text = ' '.join(texts)
    
    # 优先级1: 有弹窗需要关闭
    if '投递成功' in full_text or '已投递' in full_text:
        return 'close_popup'
    
    # 优先级2: 有投递按钮
    for e in elements:
        if '投递' in e['text'] and '成功' not in e['text'] and '已' not in e['text']:
            if e['conf'] > 0.7:
                return 'click_apply', e
    
    # 优先级3: 需要滚动找更多职位
    if '投递' not in full_text:
        return 'scroll'
    
    # 默认: 什么也不做
    return 'wait'


def execute(action):
    """执行操作"""
    if action == 'close_popup':
        print('  [ACTION] Close popup (ESC)')
        pyautogui.press('esc')
        time.sleep(1)
        return 'closed'
    
    elif isinstance(action, tuple) and action[0] == 'click_apply':
        elem = action[1]
        print(f'  [ACTION] Click apply: "{elem["text"]}" at ({elem["x"]}, {elem["y"]})')
        pyautogui.click(elem['x'], elem['y'])
        time.sleep(3)
        return 'clicked'
    
    elif action == 'scroll':
        print('  [ACTION] Scroll down')
        pyautogui.scroll(-300)
        time.sleep(2)
        return 'scrolled'
    
    elif action == 'wait':
        print('  [ACTION] Wait')
        time.sleep(2)
        return 'waited'


def deliver_one():
    """投递一个职位"""
    print('\n--- Deliver One ---')
    
    for attempt in range(5):
        print(f'\n[Attempt {attempt+1}] Scanning...')
        elements = scan()
        
        action = decide(elements)
        print(f'  Decision: {action}')
        
        result = execute(action)
        
        if result == 'clicked':
            # 点击了投递，检查结果
            time.sleep(2)
            elements = scan()
            texts = [e['text'] for e in elements]
            
            if any('成功' in t or '已投递' in t for t in texts):
                print('  [SUCCESS] Delivery confirmed!')
                pyautogui.press('esc')
                time.sleep(1)
                return True
            else:
                print('  [CHECK] Not confirmed, continue...')
        
        if result == 'closed':
            # 关闭了弹窗，说明之前投递成功了
            return True
    
    print('  [FAILED] Could not deliver')
    return False


def deliver_batch(count):
    """批量投递"""
    print('\n' + '='*60)
    print(f'Smart OCR Delivery: target {count} jobs')
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
        
        # 滚动找更多
        if i < count - 1:
            print('\nScroll for more...')
            pyautogui.scroll(-300)
            time.sleep(2)
    
    print('\n' + '='*60)
    print(f'COMPLETE: {delivered}/{count} delivered')
    print('='*60)
    
    return delivered


if __name__ == '__main__':
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    deliver_batch(count)
