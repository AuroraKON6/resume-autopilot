# -*- coding: utf-8 -*-
import easyocr
import pyautogui

print('Scanning screen...')
reader = easyocr.Reader(['ch_sim', 'en'], gpu=False, model_storage_directory='C:/Users/K-ON的学习本/.EasyOCR/model')

screenshot = pyautogui.screenshot()
screenshot.save('current.png')
results = reader.readtext('current.png')

print(f'\nFound {len(results)} elements:')
keywords = ['投递', '沟通', '申请', '简历', '已投递', '职位', 'Java', 'java', '详情', '立即']

for bbox, text, prob in results:
    x = int((bbox[0][0] + bbox[2][0]) / 2)
    y = int((bbox[0][1] + bbox[2][1]) / 2)
    for kw in keywords:
        if kw in text:
            print(f'  ({x}, {y}) "{text}" conf={prob:.2f}')
            break
