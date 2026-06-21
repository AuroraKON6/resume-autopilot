# -*- coding: utf-8 -*-
import pyautogui
import time
import easyocr

print('Clicking apply button at (1932, 311)...')
pyautogui.click(1932, 311)
time.sleep(3)

print('Checking result...')
reader = easyocr.Reader(['ch_sim', 'en'], gpu=False, model_storage_directory='C:/Users/K-ON的学习本/.EasyOCR/model')
screenshot = pyautogui.screenshot()
screenshot.save('result.png')
results = reader.readtext('result.png')

print('\nLooking for success keywords...')
keywords = ['已投递', '投递成功', '已沟通', '已申请', '已发送', '成功']
found = False
for bbox, text, prob in results:
    for kw in keywords:
        if kw in text:
            print(f'[SUCCESS] Found "{text}"')
            found = True
            break

if not found:
    print('[NOT CONFIRMED] No success message found')
    print('\nAll text on screen:')
    for bbox, text, prob in results[:20]:
        print(f'  "{text}"')
