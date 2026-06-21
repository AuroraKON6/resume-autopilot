#!/usr/bin/env python3
"""
AI视觉投递脚本
使用mimo API分析截图并自动投递

使用方式:
    python ai_deliver.py --platform boss --keyword java --count 5
"""

import sys
import os
import json
import time
import argparse
import base64
from datetime import datetime

try:
    import pyautogui
    from PIL import Image
    import openai
except ImportError:
    print("请安装依赖: pip install pyautogui pillow openai")
    sys.exit(1)

# API配置
API_KEY = "your_mimo_api_key_here"
BASE_URL = "https://token-plan-sgp.xiaomimimo.com/v1"
MODEL = "mimo-v2.5"

# 平台配置
PLATFORM_CONFIG = {
    "boss": {
        "name": "Boss直聘",
        "url": "https://www.zhipin.com/web/geek/job?query={keyword}&city=101280100",
        "objective": "在Boss直聘搜索{keyword}岗位，找到合适的职位并投递{count}个岗位"
    },
    "51job": {
        "name": "51job",
        "url": "https://we.51job.com/pc/search?keyword={keyword}&jobArea=030200",
        "objective": "在51job搜索{keyword}岗位，找到合适的职位并投递{count}个岗位"
    },
    "zhilian": {
        "name": "智联招聘",
        "url": "https://sou.zhaopin.com/?kw={keyword}&jl=763",
        "objective": "在智联招聘搜索{keyword}岗位，找到合适的职位并投递{count}个岗位"
    },
    "liepin": {
        "name": "猎聘",
        "url": "https://www.liepin.com/zhaopin/?key={keyword}&dq=050020",
        "objective": "在猎聘搜索{keyword}岗位，找到合适的职位并投递{count}个岗位"
    }
}


def take_screenshot_base64():
    """截取屏幕并返回base64编码"""
    screenshot = pyautogui.screenshot()
    screenshot.save("temp_screenshot.png")
    with open("temp_screenshot.png", "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def analyze_screenshot(image_base64, objective):
    """使用AI分析截图，返回操作建议"""
    client = openai.OpenAI(
        api_key=API_KEY,
        base_url=BASE_URL,
        timeout=30
    )
    
    prompt = f"""你是一个自动化操作助手。请分析这个屏幕截图，告诉我如何操作来完成以下任务：

任务：{objective}

请用JSON格式回复，包含以下字段：
{{
    "action": "click" 或 "type" 或 "scroll" 或 "done",
    "x": 点击位置的x坐标（如果是click）,
    "y": 点击位置的y坐标（如果是click）,
    "text": 要输入的文字（如果是type）,
    "direction": "up" 或 "down"（如果是scroll）,
    "reason": "选择这个操作的原因",
    "status": "继续" 或 "完成" 或 "失败"
}}

只回复JSON，不要有其他内容。"""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=500
        )
        
        content = response.choices[0].message.content
        # 提取JSON
        if "{" in content:
            start = content.index("{")
            end = content.rindex("}") + 1
            return json.loads(content[start:end])
        return None
    except Exception as e:
        print(f"AI分析失败: {e}")
        return None


def execute_action(action):
    """执行AI建议的操作"""
    if action is None:
        return False
    
    act = action.get("action")
    
    if act == "click":
        x, y = action.get("x", 0), action.get("y", 0)
        print(f"  点击: ({x}, {y}) - {action.get('reason', '')}")
        pyautogui.click(x, y)
        time.sleep(1)
        return True
        
    elif act == "type":
        text = action.get("text", "")
        print(f"  输入: {text}")
        pyautogui.typewrite(text, interval=0.05)
        time.sleep(0.5)
        return True
        
    elif act == "scroll":
        direction = action.get("direction", "down")
        amount = -3 if direction == "down" else 3
        print(f"  滚动: {direction}")
        pyautogui.scroll(amount)
        time.sleep(0.5)
        return True
        
    elif act == "done":
        print(f"  任务完成: {action.get('reason', '')}")
        return False
        
    return False


def deliver_on_platform(platform, keyword, count):
    """在指定平台使用AI投递"""
    config = PLATFORM_CONFIG.get(platform)
    if not config:
        return {"success": False, "error": f"不支持的平台: {platform}", "delivered": 0}
    
    url = config["url"].format(keyword=keyword)
    objective = config["objective"].format(keyword=keyword, count=count)
    
    print(f"打开浏览器: {url}")
    os.system(f'start chrome "{url}"')
    time.sleep(5)
    
    delivered = 0
    max_attempts = count * 3  # 最多尝试次数
    
    for attempt in range(max_attempts):
        if delivered >= count:
            break
            
        print(f"\n尝试 {attempt + 1}/{max_attempts}，已投递: {delivered}/{count}")
        
        # 截图
        image_base64 = take_screenshot_base64()
        
        # AI分析
        action = analyze_screenshot(image_base64, objective)
        if action:
            print(f"  AI建议: {action.get('action')} - {action.get('reason', '')}")
            
            # 执行操作
            if not execute_action(action):
                if action.get("status") == "完成":
                    break
                    
            # 如果是点击投递按钮，计数+1
            if action.get("action") == "click" and "投递" in action.get("reason", ""):
                delivered += 1
                
        time.sleep(2)
    
    return {
        "success": delivered > 0,
        "platform": platform,
        "keyword": keyword,
        "attempted": count,
        "delivered": delivered,
        "skipped": count - delivered,
        "needsUserAction": delivered < count,
        "timestamp": datetime.now().isoformat()
    }


def main():
    parser = argparse.ArgumentParser(description="AI视觉投递脚本")
    parser.add_argument("--platform", "-p", required=True,
                        choices=["boss", "51job", "zhilian", "liepin"])
    parser.add_argument("--keyword", "-k", required=True)
    parser.add_argument("--count", "-c", type=int, default=5)
    
    args = parser.parse_args()
    
    print(f"=" * 60)
    print(f"AI视觉投递")
    print(f"平台: {args.platform}")
    print(f"关键词: {args.keyword}")
    print(f"目标: {args.count}个")
    print(f"=" * 60)
    
    result = deliver_on_platform(args.platform, args.keyword, args.count)
    
    print("\n" + "=" * 60)
    print("结果:")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("=" * 60)
    
    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()
