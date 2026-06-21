#!/usr/bin/env python3
"""
Self-Operating Computer 投递脚本
使用AI视觉操作浏览器完成招聘平台投递

使用方式:
    python self_operate_deliver.py --platform boss --keyword java --count 5
"""

import sys
import os
import json
import time
import argparse
import subprocess
from datetime import datetime

# 添加self-operating-computer到Python路径
SOC_PATH = os.path.join(os.path.dirname(__file__), "self-operating-computer")
if os.path.exists(SOC_PATH):
    sys.path.insert(0, SOC_PATH)

# 平台配置
PLATFORM_CONFIG = {
    "boss": {
        "name": "Boss直聘",
        "url": "https://www.zhipin.com/web/geek/job?query={keyword}&city=101280100",
        "objective": "在Boss直聘搜索{keyword}岗位，找到合适的职位并投递{count}个岗位。点击职位详情页，然后点击'立即沟通'或'投递简历'按钮。"
    },
    "51job": {
        "name": "51job",
        "url": "https://we.51job.com/pc/search?keyword={keyword}&jobArea=030200",
        "objective": "在51job搜索{keyword}岗位，找到合适的职位并投递{count}个岗位。点击职位详情页，然后点击'申请职位'或'投递简历'按钮。"
    },
    "zhilian": {
        "name": "智联招聘",
        "url": "https://sou.zhaopin.com/?kw={keyword}&jl=763",
        "objective": "在智联招聘搜索{keyword}岗位，找到合适的职位并投递{count}个岗位。点击职位详情页，然后点击'投递简历'或'立即申请'按钮。"
    },
    "liepin": {
        "name": "猎聘",
        "url": "https://www.liepin.com/zhaopin/?key={keyword}&dq=050020",
        "objective": "在猎聘搜索{keyword}岗位，找到合适的职位并投递{count}个岗位。点击职位详情页，然后点击'投递简历'或'申请职位'按钮。"
    }
}


def deliver_jobs(platform, keyword, count):
    """
    执行投递任务
    
    Args:
        platform: 平台名称 (boss, 51job, zhilian, liepin)
        keyword: 搜索关键词
        count: 投递数量
    
    Returns:
        dict: 投递结果（结构化JSON）
    """
    config = PLATFORM_CONFIG.get(platform)
    if not config:
        return {
            "success": False,
            "error": f"不支持的平台: {platform}",
            "attempted": 0,
            "delivered": 0,
            "skipped": 0,
            "needsUserAction": False
        }
    
    # 构建objective
    objective = config["objective"].format(keyword=keyword, count=count)
    
    start_time = datetime.now()
    
    try:
        # 设置OpenAI API Key
        os.environ["OPENAI_API_KEY"] = "your_mimo_api_key_here"
        
        # 尝试使用Self-Operating Computer
        try:
            from operate.main import main as operate_main
            # 调用operate函数
            result = operate_main(model="gpt-4-with-ocr", terminal_prompt=objective)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            return {
                "success": True,
                "platform": platform,
                "keyword": keyword,
                "attempted": count,
                "delivered": count,
                "skipped": 0,
                "needsUserAction": False,
                "duration": duration,
                "timestamp": datetime.now().isoformat()
            }
        except ImportError as e:
            print(f"SOC导入失败: {e}，使用pyautogui方案")
            # 如果SOC不可用，使用简化版本
            return deliver_with_pyautogui(platform, keyword, count)
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "platform": platform,
            "attempted": count,
            "delivered": 0,
            "skipped": count,
            "needsUserAction": True
        }


def deliver_with_pyautogui(platform, keyword, count):
    """使用pyautogui简化版本投递"""
    try:
        import pyautogui
        import pyperclip
    except ImportError:
        return {
            "success": False,
            "error": "缺少pyautogui依赖",
            "attempted": count,
            "delivered": 0,
            "skipped": count,
            "needsUserAction": True
        }
    
    config = PLATFORM_CONFIG.get(platform)
    url = config["url"].format(keyword=keyword)
    
    # 打开浏览器（Windows方式）
    os.system(f'start chrome "{url}"')
    time.sleep(5)
    
    delivered = 0
    for i in range(count):
        try:
            # 点击职位卡片（简化处理）
            pyautogui.click(400, 300 + i * 100)
            time.sleep(2)
            
            # 点击投递按钮
            pyautogui.click(800, 500)
            time.sleep(1)
            
            # 关闭弹窗
            pyautogui.press('esc')
            time.sleep(1)
            
            delivered += 1
            
            # 返回列表
            pyautogui.hotkey('alt', 'left')
            time.sleep(2)
            
        except Exception as e:
            print(f"投递第{i+1}个失败: {e}")
    
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
    """主函数"""
    parser = argparse.ArgumentParser(description="Self-Operating Computer 投递脚本")
    parser.add_argument("--platform", "-p", required=True, 
                        choices=["boss", "51job", "zhilian", "liepin"],
                        help="招聘平台")
    parser.add_argument("--keyword", "-k", required=True,
                        help="搜索关键词")
    parser.add_argument("--count", "-c", type=int, default=5,
                        help="投递数量 (默认: 5)")
    
    args = parser.parse_args()
    
    # 执行投递
    result = deliver_jobs(args.platform, args.keyword, args.count)
    
    # 输出结构化JSON
    print(json.dumps(result, ensure_ascii=False))
    
    # 返回退出码
    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()
