# -*- coding: utf-8 -*-
import pyautogui
import easyocr
import time

reader = easyocr.Reader(['ch_sim', 'en'], gpu=False, model_storage_directory='C:/Users/K-ON的学习本/.EasyOCR/model')

# 找投递按钮
screenshot = pyautogui.screenshot()
screenshot.save('screen.png')
results = reader.readtext('screen.png')

for bbox, text, prob in results:
    if '投递' in text and '成功' not in text:
        x = int((bbox[0][0] + bbox[2][0]) / 2)
        y = int((bbox[0][1] + bbox[2][1]) / 2)
        print(f'Apply: ({x}, {y}) "{text}"')
        pyautogui.click(x, y)
        time.sleep(3)
        break

# 扫描弹窗
print('\nScanning popup...')
screenshot = pyautogui.screenshot()
screenshot.save('popup.png')
results = reader.readtext('popup.png')

print('All text on popup:')
for bbox, text, prob in results:
    if prob > 0.3:
        x = int((bbox[0][0] + bbox[2][0]) / 2)
        y = int((bbox[0][1] + bbox[2][1]) / 2)
        print(f'  ({x}, {y}) "{text}"')
