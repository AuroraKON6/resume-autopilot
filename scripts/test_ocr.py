# -*- coding: utf-8 -*-
import easyocr
import pyautogui

print('Loading OCR model...')
reader = easyocr.Reader(['ch_sim', 'en'], gpu=False, model_storage_directory='C:/Users/K-ON的学习本/.EasyOCR/model')

print('Taking screenshot...')
screenshot = pyautogui.screenshot()
screenshot.save('ocr_test.png')

print('Running OCR...')
results = reader.readtext('ocr_test.png')

print(f'Found {len(results)} text elements:')
for i, (bbox, text, prob) in enumerate(results[:15]):
    x = int((bbox[0][0] + bbox[2][0]) / 2)
    y = int((bbox[0][1] + bbox[2][1]) / 2)
    print(f'  [{i}] ({x}, {y}) "{text}" conf={prob:.2f}')
