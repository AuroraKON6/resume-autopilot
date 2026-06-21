#!/usr/bin/env python3
"""
真正的AI视觉投递脚�?截图 -> AI识别 -> 点击 -> 等待 -> 确认

使用方式:
    python ai_deliver_real.py --platform boss --keyword java --count 1
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
    print("请安装依�? pip install pyautogui pillow openai")
    sys.exit(1)

# API配置
API_KEY = "your_mimo_api_key_here"
BASE_URL = "https://token-plan-sgp.xiaomimimo.com/v1"
MODEL = "mimo-v2.5"

# 平台配置
PLATFORM_URLS = {
    "boss": "https://www.zhipin.com/web/geek/job?query={keyword}&city=101280100",
    "51job": "https://we.51job.com/pc/search?keyword={keyword}&jobArea=030200",
    "zhilian": "https://sou.zhaopin.com/?kw={keyword}&jl=763",
    "liepin": "https://www.liepin.com/zhaopin/?key={keyword}&dq=050020"
}


def take_screenshot_base64(max_size=800):
    """截取屏幕并返回base64编码（压缩版�?""
    screenshot = pyautogui.screenshot()
    # 缩小图片以加快API响应
    screenshot = screenshot.resize((max_size, int(max_size * screenshot.height / screenshot.width)))
    screenshot.save("temp_screenshot.png", quality=60)
    with open("temp_screenshot.png", "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def ai_analyze(image_base64, prompt):
    """调用AI分析截图"""
    client = openai.OpenAI(
        api_key=API_KEY,
        base_url=BASE_URL,
        timeout=30
    )
    
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
        if content:
            return content
        return None
    except Exception as e:
        print(f"  AI分析失败: {e}")
        return None


def find_and_click_job(image_base64):
    """AI识别职位并返回点击坐�?""
    prompt = """请分析这个招聘网站截图，找到第一个职位卡片�?
用JSON格式回复�?{
    "found": true,
    "job_title": "职位名称",
    "x": 点击位置的x坐标,
    "y": 点击位置的y坐标,
    "reason": "选择原因"
}

如果没找到职位，返回 {"found": false}
只回复JSON，不要有其他内容�?""

    result = ai_analyze(image_base64, prompt)
    if result:
        try:
            # 提取JSON
            if "{" in result:
                start = result.index("{")
                end = result.rindex("}") + 1
                return json.loads(result[start:end])
        except:
            pass
    return None


def find_apply_button(image_base64):
    """AI识别投递按�?""
    prompt = """请分析这个招聘网站截图，找到"投递简�?�?立即沟�?�?申请职位"或类似的投�?申请按钮�?
用JSON格式回复�?{
    "found": true,
    "button_text": "按钮文字",
    "x": 按钮中心的x坐标,
    "y": 按钮中心的y坐标
}

如果没找到按钮，返回 {"found": false}
只回复JSON，不要有其他内容�?""

    result = ai_analyze(image_base64, prompt)
    if result:
        try:
            if "{" in result:
                start = result.index("{")
                end = result.rindex("}") + 1
                return json.loads(result[start:end])
        except:
            pass
    return None


def check_delivery_success(image_base64):
    """检查是否投递成�?""
    prompt = """请分析这个截图，判断是否投递成功�?
投递成功的标志�?- 出现"投递成�?�?已投�?�?已申�?等文�?- 按钮变为"已投�?状�?- 出现"已沟�?等状�?
用JSON格式回复�?{
    "success": true,
    "message": "投递成功原�?
}

如果投递不成功，返回：
{
    "success": false,
    "reason": "失败原因"
}

只回复JSON，不要有其他内容�?""

    result = ai_analyze(image_base64, prompt)
    if result:
        try:
            if "{" in result:
                start = result.index("{")
                end = result.rindex("}") + 1
                return json.loads(result[start:end])
        except:
            pass
    return None


def deliver_one_job(platform, keyword):
    """投递一个职位的完整流程"""
    print(f"\n{'='*50}")
    print(f"开始投递流�?)
    print(f"{'='*50}")
    
    # 步骤1: 截图找职�?    print("\n[步骤1] 截图找职�?..")
    image_base64 = take_screenshot_base64()
    job_info = find_and_click_job(image_base64)
    
    if not job_info or not job_info.get("found"):
        print("  未找到职�?)
        return False
    
    print(f"  找到职位: {job_info.get('job_title')}")
    print(f"  点击位置: ({job_info.get('x')}, {job_info.get('y')})")
    
    # 步骤2: 点击职位
    print("\n[步骤2] 点击职位...")
    x, y = job_info.get("x"), job_info.get("y")
    pyautogui.click(x, y)
    time.sleep(3)  # 等待页面加载
    
    # 步骤3: 截图找投递按�?    print("\n[步骤3] 截图找投递按�?..")
    image_base64 = take_screenshot_base64()
    apply_btn = find_apply_button(image_base64)
    
    if not apply_btn or not apply_btn.get("found"):
        print("  未找到投递按钮，返回列表")
        pyautogui.hotkey("alt", "left")
        time.sleep(2)
        return False
    
    print(f"  找到按钮: {apply_btn.get('button_text')}")
    print(f"  点击位置: ({apply_btn.get('x')}, {apply_btn.get('y')})")
    
    # 步骤4: 点击投递按�?    print("\n[步骤4] 点击投递按�?..")
    x, y = apply_btn.get("x"), apply_btn.get("y")
    pyautogui.click(x, y)
    time.sleep(3)  # 等待投递处�?    
    # 步骤5: 截图确认投递成�?    print("\n[步骤5] 截图确认投递结�?..")
    image_base64 = take_screenshot_base64()
    result = check_delivery_success(image_base64)
    
    if result and result.get("success"):
        print(f"  �?投递成�? {result.get('message')}")
        # 关闭可能的弹�?        pyautogui.press("esc")
        time.sleep(1)
        # 返回列表
        pyautogui.hotkey("alt", "left")
        time.sleep(2)
        return True
    else:
        reason = result.get("reason", "未知") if result else "无法判断"
        print(f"  �?投递未确认: {reason}")
        # 关闭可能的弹�?        pyautogui.press("esc")
        time.sleep(1)
        # 返回列表
        pyautogui.hotkey("alt", "left")
        time.sleep(2)
        return False


def deliver_on_platform(platform, keyword, count):
    """在指定平台投递多个职�?""
    url = PLATFORM_URLS.get(platform, "").format(keyword=keyword)
    
    print(f"\n{'='*60}")
    print(f"AI视觉投�?)
    print(f"平台: {platform}")
    print(f"关键�? {keyword}")
    print(f"目标: {count}�?)
    print(f"{'='*60}")
    
    # 打开浏览�?    print(f"\n打开浏览�? {url}")
    os.system(f'start chrome "{url}"')
    time.sleep(5)
    
    delivered = 0
    
    for i in range(count):
        print(f"\n{'='*50}")
        print(f"投递第 {i+1}/{count} �?)
        print(f"{'='*50}")
        
        success = deliver_one_job(platform, keyword)
        if success:
            delivered += 1
            print(f"\n[成功] 已成功投�?{delivered}/{count} �?)
        else:
            print(f"\n[失败] 投递失败，继续下一�?)
        
        time.sleep(2)
    
    print(f"\n{'='*60}")
    print(f"投递完�? {delivered}/{count} 个成�?)
    print(f"{'='*60}")
    
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
    parser = argparse.ArgumentParser(description="AI视觉投递脚�?)
    parser.add_argument("--platform", "-p", required=True,
                        choices=["boss", "51job", "zhilian", "liepin"])
    parser.add_argument("--keyword", "-k", required=True)
    parser.add_argument("--count", "-c", type=int, default=1)
    
    args = parser.parse_args()
    
    result = deliver_on_platform(args.platform, args.keyword, args.count)
    
    print("\n" + json.dumps(result, ensure_ascii=False, indent=2))
    
    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()
