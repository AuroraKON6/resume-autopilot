# -*- coding: utf-8 -*-
import pyautogui
import time
import easyocr

print('Clicking apply at (1767, 1046)...')
pyautogui.click(1767, 1046)
time.sleep(3)

print('Checking result...')
reader = easyocr.Reader(['ch_sim', 'en'], gpu=False, model_storage_directory='C:/Users/K-ON的学习本/.EasyOCR/model')
screenshot = pyautogui.screenshot()
screenshot.save('result.png')
results = reader.readtext('result.png')

keywords = ['已投递', '投递成功', '已申请', '成功', '已发送']
found = False
for bbox, text, prob in results:
    for kw in keywords:
        if kw in text:
            print(f'[SUCCESS] Found: "{text}"')
            found = True
            break

if not found:
    print('[NOT CONFIRMED]')
    print('Screen text:')
    for bbox, text, prob in results[:15]:
        if prob > 0.5:
            print(f'  "{text}"')
