#!/usr/bin/env python3
"""
简化版投递脚本
使用pyautogui + 截图分析实现自动化投递

使用方式:
    python simple_deliver.py --platform boss --keyword java --count 5
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
pyautogui.FAILSAFE = True  # 鼠标移到左上角可中断
pyautogui.PAUSE = 0.5  # 每个操作间隔0.5秒

# 平台配置
PLATFORM_CONFIG = {
    "boss": {
        "name": "Boss直聘",
        "url": "https://www.zhipin.com",
        "search_box": None,  # 需要通过图像识别找到
        "apply_button": None,
    },
    "51job": {
        "name": "51job",
        "url": "https://www.51job.com",
        "search_box": None,
        "apply_button": None,
    },
    "zhilian": {
        "name": "智联招聘",
        "url": "https://www.zhaopin.com",
        "search_box": None,
        "apply_button": None,
    },
    "liepin": {
        "name": "猎聘",
        "url": "https://www.liepin.com",
        "search_box": None,
        "apply_button": None,
    }
}


def take_screenshot(filename=None):
    """截取屏幕"""
    if filename is None:
        filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    screenshot = pyautogui.screenshot()
    screenshot.save(filename)
    return filename


def find_and_click_image(image_path, confidence=0.8):
    """查找并点击图像"""
    try:
        location = pyautogui.locateOnScreen(image_path, confidence=confidence)
        if location:
            center = pyautogui.center(location)
            pyautogui.click(center)
            return True
    except Exception as e:
        print(f"未找到图像: {e}")
    return False


def type_text(text):
    """输入文本"""
    pyperclip.copy(text)
    pyautogui.hotkey('ctrl', 'v')
    time.sleep(0.5)


def open_url(url):
    """打开URL"""
    # 打开浏览器
    pyautogui.hotkey('win', 'r')
    time.sleep(1)
    type_text(f"chrome {url}")
    pyautogui.press('enter')
    time.sleep(3)


def scroll_down(times=3):
    """向下滚动"""
    for _ in range(times):
        pyautogui.scroll(-3)
        time.sleep(0.5)


def scroll_up(times=3):
    """向上滚动"""
    for _ in range(times):
        pyautogui.scroll(3)
        time.sleep(0.5)


def deliver_on_boss(keyword, count):
    """在Boss直聘投递"""
    print(f"开始Boss直聘投递: {keyword}")
    
    # 打开Boss直聘
    open_url(f"https://www.zhipin.com/web/geek/job?query={keyword}&city=101280100")
    time.sleep(5)
    
    delivered = 0
    for i in range(count):
        print(f"投递第 {i+1}/{count} 个...")
        
        # 截图分析当前页面
        screenshot = take_screenshot()
        
        # 尝试点击职位卡片
        # 这里需要根据实际页面布局调整
        # 可以使用图像识别或坐标点击
        
        # 点击第一个职位
        pyautogui.click(400, 300)  # 假设第一个职位在这个位置
        time.sleep(2)
        
        # 点击投递按钮
        # 需要找到"立即沟通"或"投递简历"按钮
        pyautogui.click(800, 500)  # 假设按钮在这个位置
        time.sleep(1)
        
        # 按ESC关闭弹窗
        pyautogui.press('esc')
        time.sleep(1)
        
        delivered += 1
        
        # 返回列表页
        pyautogui.hotkey('alt', 'left')
        time.sleep(2)
    
    return delivered


def deliver_on_51job(keyword, count):
    """在51job投递"""
    print(f"开始51job投递: {keyword}")
    
    # 打开51job
    open_url(f"https://we.51job.com/pc/search?keyword={keyword}&jobArea=030200")
    time.sleep(5)
    
    delivered = 0
    for i in range(count):
        print(f"投递第 {i+1}/{count} 个...")
        
        # 点击职位
        pyautogui.click(400, 300)
        time.sleep(2)
        
        # 点击申请职位
        pyautogui.click(800, 500)
        time.sleep(1)
        
        delivered += 1
        
        # 返回
        pyautogui.hotkey('alt', 'left')
        time.sleep(2)
    
    return delivered


def deliver_on_zhilian(keyword, count):
    """在智联招聘投递"""
    print(f"开始智联招聘投递: {keyword}")
    
    # 打开智联招聘
    open_url(f"https://sou.zhaopin.com/?kw={keyword}&jl=763")
    time.sleep(5)
    
    delivered = 0
    for i in range(count):
        print(f"投递第 {i+1}/{count} 个...")
        
        # 点击职位
        pyautogui.click(400, 300)
        time.sleep(2)
        
        # 点击投递简历
        pyautogui.click(800, 500)
        time.sleep(1)
        
        delivered += 1
        
        # 返回
        pyautogui.hotkey('alt', 'left')
        time.sleep(2)
    
    return delivered


def deliver_on_liepin(keyword, count):
    """在猎聘投递"""
    print(f"开始猎聘投递: {keyword}")
    
    # 打开猎聘
    open_url(f"https://www.liepin.com/zhaopin/?key={keyword}&dq=050020")
    time.sleep(5)
    
    delivered = 0
    for i in range(count):
        print(f"投递第 {i+1}/{count} 个...")
        
        # 点击职位
        pyautogui.click(400, 300)
        time.sleep(2)
        
        # 点击投递简历
        pyautogui.click(800, 500)
        time.sleep(1)
        
        delivered += 1
        
        # 返回
        pyautogui.hotkey('alt', 'left')
        time.sleep(2)
    
    return delivered


# 投递函数映射
DELIVER_FUNCTIONS = {
    "boss": deliver_on_boss,
    "51job": deliver_on_51job,
    "zhilian": deliver_on_zhilian,
    "liepin": deliver_on_liepin,
}


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="简化版投递脚本")
    parser.add_argument("--platform", "-p", required=True,
                        choices=["boss", "51job", "zhilian", "liepin"],
                        help="招聘平台")
    parser.add_argument("--keyword", "-k", required=True,
                        help="搜索关键词")
    parser.add_argument("--count", "-c", type=int, default=5,
                        help="投递数量 (默认: 5)")
    parser.add_argument("--dry-run", action="store_true",
                        help="试运行模式")
    
    args = parser.parse_args()
    
    print(f"=" * 60)
    print(f"投递任务")
    print(f"平台: {args.platform}")
    print(f"关键词: {args.keyword}")
    print(f"目标数量: {args.count}")
    print(f"=" * 60)
    
    if args.dry_run:
        print("试运行模式，不执行实际操作")
        return
    
    # 检查是否在虚拟环境
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("警告: 建议在虚拟环境中运行")
    
    # 执行投递
    deliver_func = DELIVER_FUNCTIONS.get(args.platform)
    if not deliver_func:
        print(f"不支持的平台: {args.platform}")
        sys.exit(1)
    
    start_time = datetime.now()
    
    try:
        delivered = deliver_func(args.keyword, args.count)
        
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
