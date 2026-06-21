# -*- coding: utf-8 -*-
import easyocr
import pyautogui

reader = easyocr.Reader(['ch_sim', 'en'], gpu=False, model_storage_directory='C:/Users/K-ON的学习本/.EasyOCR/model')
screenshot = pyautogui.screenshot()
screenshot.save('screen.png')
results = reader.readtext('screen.png')

print('Looking for close buttons:')
for bbox, text, prob in results:
    if 'X' in text or 'x' in text or '关' in text or '闭' in text:
        x = int((bbox[0][0] + bbox[2][0]) / 2)
        y = int((bbox[0][1] + bbox[2][1]) / 2)
        print(f'  ({x}, {y}) "{text}" conf={prob:.2f}')
