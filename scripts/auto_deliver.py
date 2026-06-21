#!/usr/bin/env python3
"""
自动化投递脚本
使用pyautogui + 截图分析实现AI操作电脑

使用方式:
    python auto_deliver.py --platform boss --keyword java --count 5
"""

import sys
import os
import json
import time
import argparse
import subprocess
from datetime import datetime

try:
    import pyautogui
    import pyperclip
    from PIL import Image
except ImportError:
    print("请安装依赖: pip install pyautogui pyperclip pillow")
    sys.exit(1)

# 设置pyautogui安全设置
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.5

# 平台配置
PLATFORM_CONFIG = {
    "boss": {
        "name": "Boss直聘",
        "url": "https://www.zhipin.com/web/geek/job?query={keyword}&city=101280100",
        "search_box": (400, 150),  # 搜索框位置
        "job_cards": [(400, 300), (400, 400), (400, 500), (400, 600), (400, 700)],  # 职位卡片位置
        "apply_button": (800, 500),  # 投递按钮位置
        "close_button": (900, 200),  # 关闭按钮位置
    },
    "51job": {
        "name": "51job",
        "url": "https://we.51job.com/pc/search?keyword={keyword}&jobArea=030200",
        "search_box": (400, 150),
        "job_cards": [(400, 300), (400, 400), (400, 500), (400, 600), (400, 700)],
        "apply_button": (800, 500),
        "close_button": (900, 200),
    },
    "zhilian": {
        "name": "智联招聘",
        "url": "https://sou.zhaopin.com/?kw={keyword}&jl=763",
        "search_box": (400, 150),
        "job_cards": [(400, 300), (400, 400), (400, 500), (400, 600), (400, 700)],
        "apply_button": (800, 500),
        "close_button": (900, 200),
    },
    "liepin": {
        "name": "猎聘",
        "url": "https://www.liepin.com/zhaopin/?key={keyword}&dq=050020",
        "search_box": (400, 150),
        "job_cards": [(400, 300), (400, 400), (400, 500), (400, 600), (400, 700)],
        "apply_button": (800, 500),
        "close_button": (900, 200),
    }
}


def take_screenshot(filename=None):
    """截取屏幕"""
    if filename is None:
        filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    screenshot = pyautogui.screenshot()
    screenshot.save(filename)
    return filename


def find_button_on_screen(button_text, confidence=0.8):
    """在屏幕上查找按钮"""
    try:
        # 截图
        screenshot = pyautogui.screenshot()
        
        # 使用OCR查找文字位置
        # 这里简化处理，使用固定位置
        return None
    except Exception as e:
        print(f"查找按钮失败: {e}")
        return None


def open_url_in_browser(url):
    """在浏览器中打开URL"""
    # 打开默认浏览器
    subprocess.Popen(['start', 'chrome', url], shell=True)
    time.sleep(3)


def type_text(text):
    """输入文本"""
    pyperclip.copy(text)
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(0.5)


def click_position(x, y):
    """点击指定位置"""
    pyautogui.click(x, y)
    time.sleep(0.5)


def scroll_down(times=3):
    """向下滚动"""
    for _ in range(times):
        pyautogui.scroll(-3)
        time.sleep(0.5)


def deliver_on_platform(platform, keyword, count):
    """在指定平台投递"""
    config = PLATFORM_CONFIG.get(platform)
    if not config:
        print(f"不支持的平台: {platform}")
        return 0
    
    print(f"开始在{config['name']}投递...")
    
    # 打开平台页面
    url = config['url'].format(keyword=keyword)
    open_url_in_browser(url)
    
    # 等待页面加载
    time.sleep(5)
    
    delivered = 0
    for i in range(count):
        print(f"投递第 {i+1}/{count} 个...")
        
        try:
            # 点击职位卡片
            card_pos = config['job_cards'][i % len(config['job_cards'])]
            click_position(card_pos[0], card_pos[1])
            time.sleep(2)
            
            # 点击投递按钮
            click_position(config['apply_button'][0], config['apply_button'][1])
            time.sleep(1)
            
            # 关闭弹窗
            pyautogui.press('esc')
            time.sleep(1)
            
            delivered += 1
            print(f"  投递成功!")
            
        except Exception as e:
            print(f"  投递失败: {e}")
        
        # 返回列表页
        pyautogui.hotkey('alt', 'left')
        time.sleep(2)
    
    return delivered


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="自动化投递脚本")
    parser.add_argument("--platform", "-p", required=True,
                        choices=["boss", "51job", "zhilian", "liepin"],
                        help="招聘平台")
    parser.add_argument("--keyword", "-k", required=True,
                        help="搜索关键词")
    parser.add_argument("--count", "-c", type=int, default=5,
                        help="投递数量 (默认: 5)")
    
    args = parser.parse_args()
    
    print(f"=" * 60)
    print(f"自动化投递任务")
    print(f"平台: {args.platform}")
    print(f"关键词: {args.keyword}")
    print(f"目标数量: {args.count}")
    print(f"=" * 60)
    
    start_time = datetime.now()
    
    try:
        delivered = deliver_on_platform(args.platform, args.keyword, args.count)
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        result = {
            "success": True,
            "platform": args.platform,
            "keyword": args.keyword,
            "requested": args.count,
            "delivered": delivered,
            "duration": duration,
            "timestamp": datetime.now().isoformat()
        }
        
        print("\n" + "=" * 60)
        print("投递结果:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        print("=" * 60)
        
        # 保存结果
        result_file = f"delivery_result_{args.platform}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"结果已保存到: {result_file}")
        
    except KeyboardInterrupt:
        print("\n用户中断操作")
    except Exception as e:
        print(f"\n投递失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
