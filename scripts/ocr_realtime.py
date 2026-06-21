# -*- coding: utf-8 -*-
"""
OCR实时检测 + 点击，不记固定位置
"""
import pyautogui
import easyocr
import time

print('Loading OCR...')
reader = easyocr.Reader(['ch_sim', 'en'], gpu=False,
                        model_storage_directory='C:/Users/K-ON的学习本/.EasyOCR/model')


def scan_and_find(keywords):
    """扫描屏幕，找包含关键词的文字，返回位置"""
    screenshot = pyautogui.screenshot()
    screenshot.save('screen.png')
    results = reader.readtext('screen.png')
    
    found = []
    for bbox, text, prob in results:
        for kw in keywords:
            if kw in text:
                x = int((bbox[0][0] + bbox[2][0]) / 2)
                y = int((bbox[0][1] + bbox[2][1]) / 2)
                found.append({'text': text, 'x': x, 'y': y, 'conf': prob})
                break
    return found


def click_element(element):
    """点击元素"""
    print(f'  Clicking: "{element["text"]}" at ({element["x"]}, {element["y"]})')
    pyautogui.click(element['x'], element['y'])


def close_popup():
    """关闭弹窗 - 实时检测X按钮"""
    print('\n[Close] Scanning for close button...')
    # 找X或关闭按钮
    results = scan_and_find(['X', 'x', '关闭', '×', '知道了', '确定'])
    
    # 过滤掉太靠边的X（通常是浏览器标签的X）
    for elem in results:
        if elem['y'] > 100 and elem['y'] < 800:  # 在页面中间区域
            print(f'  Found close: "{elem["text"]}"')
            click_element(elem)
            time.sleep(1)
            return True
    
    # 如果没找到，按ESC
    print('  No close button found, pressing ESC')
    pyautogui.press('esc')
    return True


print('=== Test: Scan and Click ===')

# 1. 扫描找投递按钮
print('\n[1] Scanning for apply button...')
apply_btns = scan_and_find(['投递', '申请', '沟通'])

if apply_btns:
    btn = apply_btns[0]
    print(f'  Found: "{btn["text"]}" at ({btn["x"]}, {btn["y"]})')
    
    # 2. 点击投递
    print('\n[2] Clicking apply...')
    click_element(btn)
    time.sleep(3)
    
    # 3. 扫描检查是否成功
    print('\n[3] Scanning for success...')
    success = scan_and_find(['已投递', '投递成功', '成功', '已申请'])
    
    if success:
        print(f'  [SUCCESS] Found: "{success[0]["text"]}"')
        
        # 4. 关闭弹窗
        print('\n[4] Closing popup...')
        close_popup()
    else:
        print('  [NOT CONFIRMED]')
else:
    print('  No apply button found')
    # 显示当前屏幕内容
    print('\nCurrent screen:')
    screenshot = pyautogui.screenshot()
    screenshot.save('screen.png')
    results = reader.readtext('screen.png')
    for bbox, text, prob in results[:10]:
        if prob > 0.5:
            print(f'  "{text}"')
