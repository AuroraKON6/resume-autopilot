# -*- coding: utf-8 -*-
import pyautogui
import easyocr
import time

reader = easyocr.Reader(['ch_sim', 'en'], gpu=False, model_storage_directory='C:/Users/K-ON的学习本/.EasyOCR/model')

print('Step 1: Find and click apply button')
screenshot = pyautogui.screenshot()
screenshot.save('screen.png')
results = reader.readtext('screen.png')

apply_btn = None
for bbox, text, prob in results:
    if '投递' in text and '成功' not in text and prob > 0.8:
        x = int((bbox[0][0] + bbox[2][0]) / 2)
        y = int((bbox[0][1] + bbox[2][1]) / 2)
        apply_btn = {'x': x, 'y': y, 'text': text}
        break

if apply_btn:
    print(f'  Found: "{apply_btn["text"]}" at ({apply_btn["x"]}, {apply_btn["y"]})')
    pyautogui.click(apply_btn['x'], apply_btn['y'])
    
    print('\nStep 2: Wait and scan popup immediately')
    time.sleep(2)
    
    screenshot = pyautogui.screenshot()
    screenshot.save('popup.png')
    results = reader.readtext('popup.png')
    
    print('Popup content:')
    for bbox, text, prob in results:
        if prob > 0.3:
            x = int((bbox[0][0] + bbox[2][0]) / 2)
            y = int((bbox[0][1] + bbox[2][1]) / 2)
            print(f'  ({x}, {y}) "{text}" conf={prob:.2f}')
else:
    print('  No apply button found')
