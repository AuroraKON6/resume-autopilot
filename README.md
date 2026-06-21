# Resume Autopilot 🚀

你的AI求职自动驾驶仪 —— 自动采集、智能匹配、一键投递，支持 Boss直聘、智联招聘、51Job、猎聘四大平台。

> 别人海投100份简历等回复，你喝咖啡的时间AI已经帮你精准投了50份。

## 架构

```
后端: Spring Boot 3 + Java 21
前端: Vue 3 + Vite
数据库: SQLite（可选 MySQL）
浏览器自动化: Playwright（平台采集/投递）
桌面自动化: Python + Mimo OCR（截图→AI识别→操作）
AI: Deepseek / OpenAI 兼容 LLM（职位匹配 + 话术生成）
```

## 工作流程

```
1. 配置公共信息（AI Key、黑名单、候选人画像）
2. 配置平台检索条件（关键词、城市、薪资、学历等）
3. 系统通过 Playwright 自动登录并采集岗位
4. 黑名单过滤 + AI 匹配评分
5. AI 生成个性化打招呼话术
6. 自动投递简历
7. 多平台轮询投递（Round-Robin）
```

## 支持平台

| 平台 | 代码 | 采集 | 投递 |
|------|------|------|------|
| Boss直聘 | `boss` | ✅ | ✅ |
| 智联招聘 | `zhilian` | ✅ | ✅ |
| 51Job | `51job` | ✅ | ✅ |
| 猎聘 | `liepin` | ✅ | ✅ |

## 快速开始

### 环境要求

- Java 17+（推荐 JDK 21）
- Python 3.11+（用于 OCR 脚本）
- Node.js 18+（前端构建，可选）

### 启动

```bash
# 1. 下载 Release 中的 jar 和 lib.zip
# 2. 解压 lib.zip 到 target/lib/
# 3. 复制 .env.example 为 .env，填入配置
# 4. 运行
start-get-jobs.cmd
```

启动后访问 http://localhost:8081

### 配置

复制 `.env.example` 为 `.env`：

```env
# AI 模型配置
DEEPSEEK_API_KEY=your_key_here
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash

# Mimo 视觉 API（用于 OCR 桌面自动化）
OPENAI_API_KEY=your_mimo_key
OPENAI_BASE_URL=https://token-plan-sgp.xiaomimimo.com/v1
MIMO_MODEL=mimo-v2.5

# Python 路径
PYTHON_EXECUTABLE=python
```

## 核心功能

### 多平台投递

每个平台独立的 TaskService，支持：
- 关键词搜索采集
- 黑名单过滤（岗位关键词、公司名）
- Cookie 持久化（自动恢复登录状态）
- 反爬虫检测绕过（Stealth 脚本）

### AI 职位匹配

基于 LLM 分析简历与岗位 JD 的匹配度：
- 解析候选人画像（技能、经验、意向）
- 对比岗位描述
- 输出匹配评分和理由

### AI 话术生成

根据岗位要求自动生成个性化打招呼消息：
- 提取 JD 关键词
- 结合候选人背景
- 控制长度和关键词覆盖率
- A/B 测试不同话术模板

### 企业评估

AI 分析公司风险：
- 公司基本信息
- 历史评价
- 风险等级评估

### OCR 桌面自动化

`scripts/mimo_ocr_agent.py` 实现截图→AI识别→操作的循环：
- 截取屏幕
- Mimo 视觉模型识别界面元素
- AI 决策下一步操作
- 执行点击/输入等操作
- 支持登录检测、验证码暂停

### 简历优化

内置 VitaPolish 模块：
- 多种简历模板（ArtDeco、Cyberpunk、Glassmorphism 等）
- AI 优化建议
- 拖拽式编辑

## 项目结构

```
├── src/main/java/getjobs/
│   ├── GetJobsApplication.java          # 入口
│   ├── controller/                      # API 控制器
│   ├── modules/
│   │   ├── ai/                          # AI 模块（匹配、话术、企业评估）
│   │   ├── getjobs/                     # 平台模块（boss/zhilian/51job/liepin）
│   │   ├── task/                        # 任务管理（快速投递、状态追踪）
│   │   ├── resume/                      # 简历管理
│   │   └── auth/                        # 认证
│   └── infrastructure/
│       ├── playwright/                  # Playwright 浏览器管理
│       ├── ai/                          # LLM 客户端
│       └── python/                      # Python 脚本调用
├── frontend/src/                        # Vue 3 前端
├── scripts/                             # Python 脚本（OCR、测试）
├── docs/                                # 文档和图片
└── start-get-jobs.cmd                   # Windows 启动脚本
```

## API 接口

| 路径 | 说明 |
|------|------|
| `POST /api/task/quick-delivery/submit/{platform}` | 快速投递 |
| `GET /api/task-execution/status/{platform}` | 任务状态 |
| `DELETE /api/task-execution/status/{platform}` | 清除任务状态 |
| `POST /api/config/{platform}` | 更新平台配置 |
| `GET /api/jobs` | 查询岗位列表 |
| `POST /api/ai/greeting` | 生成打招呼话术 |
| `POST /api/ai/job-match` | 职位匹配评估 |

## 开发

```bash
# 后端
mvn spring-boot:run -Dspring-boot.run.profiles=dev,gpt,actuator,dict

# 前端
cd frontend && npm install && npm run dev
```

## License

MIT
