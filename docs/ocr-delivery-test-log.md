# OCR 自动投递 - 测试记录

## 2026-06-22 首次投递成功

### 测试环境
- 项目路径: `E:\新的投简历用的\npe_get_jobs_temp\npe_get_jobs-main`
- Python: 3.10.7 (venv)
- 视觉模型: mimo-v2.5 (via xiaomimimo.com)
- 平台: Boss直聘
- 浏览器: Edge / Chrome
- 关键词: 市场营销实习
- 城市: 广州

### 踩过的坑

1. **mimo-v2.5-pro 不支持图片输入** — 必须用 mimo-v2.5
2. **Python requests SSL 不兼容** — venv 的 OpenSSL 1.1.1q 跟 xiaomimimo.com 的 TLS 握手失败，curl 没问题。需要 curl 子进程 fallback 或升级 requests
3. **max_tokens 太低** — mimo-v2.5 是推理模型，先思考再回答。复杂 prompt 推理要 ~1900 token，2000 不够输出 JSON。改到 1000000
4. **Chrome 不在前台** — 截屏截到的是终端窗口。需要 Windows API 聚焦浏览器窗口
5. **is_blocked 太敏感** — Boss直聘已登录时页面顶部也有"登录"文字，不能一看到就暂停

### 投递流程

```
截图 → easyocr识别 → DeepSeek文本匹配(可选) → Mimo视觉决策 → pyautogui执行 → 循环
```

### 成功投递记录

**第1次成功 (2026-06-22 23:15)**
- Step 1: 检测到页面搜索的是"python"，点击搜索框
- Step 2: 找到"[可实习] 市场助理[薪+包住"，匹配度 85，点击"立即沟通"
- Step 3: 再次点击"立即沟通"，匹配度 90
- Step 4: 检测到"已向BOSS发送消息"弹窗，done
- 岗位: 市场助理（可实习），广州千炬科技，5-10K

### 当前配置

.env 关键项:
```
VISION_API_KEY=<mimo key>
VISION_BASE_URL=https://token-plan-sgp.xiaomimimo.com/v1
VISION_MODEL=mimo-v2.5
MIMO_MODEL=mimo-v2.5
```

mimo_ocr_agent.py 关键参数:
- timeout: 300 (5分钟)
- max_tokens: 1000000
- 浏览器: Chrome 优先

### 启动命令

```bash
cd "E:/新的投简历用的/npe_get_jobs_temp/npe_get_jobs-main"
PYTHONIOENCODING=utf-8 .venv/Scripts/python.exe scripts/mimo_ocr_agent.py \
  --platform boss --keyword "市场营销实习" --count 5 \
  --max-steps 12 --auto-submit --initial-delay 8 --action-delay 3 \
  --disable-text-match
```

### 已知问题

- `delivered` 计数器不准确（成功投递了但显示 0）
- DeepSeek API Key 未配置（文本匹配功能不可用）
- 全屏截图大时 API 响应慢（~2分钟/次）
- 浏览器窗口必须在前台（pyautogui 截屏限制）

### 下一步

- [ ] 配置 DeepSeek API Key 启用文本匹配
- [ ] 测试 count=5 连续投递
- [ ] 优化 success_detected 计数逻辑
- [ ] 考虑压缩截图减少 API 响应时间

---

## 2026-06-22 Codex 后续修复

已处理：
- `delivered` 计数器：现在 Boss 成功弹窗 `已向BOSS发送消息` + `留在此页/继续沟通` 会直接计为成功。
- LLM 返回 `{"action":"done"}` 时，如果当前屏幕或 reason 表明已发送消息，也会计入 `delivered`。
- 成功后优先点击 `留在此页` 关闭弹窗，便于继续下一份岗位。
- 发给 Mimo 的截图默认压缩为 JPEG，宽度 `960`，质量 `72`，减少请求体积。
- `VISION_MAX_TOKENS` 默认改为 `4096`，不再硬编码 `1000000`。
- `VISION_TIMEOUT_SECONDS` 默认 `180`。
- 增加 `VISION_CURL_FALLBACK=true`，requests 因 SSL/TLS 失败时自动使用 curl 子进程重试。

建议下一次测试：
```powershell
$env:PYTHONIOENCODING='utf-8'
$env:TARGET_BROWSER='chrome'
$env:VISION_CURL_FALLBACK='true'

.\.venv\Scripts\python.exe scripts\mimo_ocr_agent.py `
  --platform boss `
  --keyword "市场营销实习" `
  --count 5 `
  --max-steps 12 `
  --auto-submit `
  --initial-delay 8 `
  --action-delay 3 `
  --disable-text-match
```

观察重点：
- `delivered` 是否随着成功弹窗增加。
- 成功后是否能自动关闭弹窗并进入下一份岗位。
- 每次 Mimo 响应耗时是否下降。
- `events[].outcome` 是否出现 `success_done` 或 `success_detected`。

---

## 2026-06-23 Boss 成功弹窗卡住修复

触发场景：
- Boss 页面已经显示 `已向BOSS发送消息` 弹窗，但自动流程停在弹窗上，没有继续下一步。
- 真实截图 OCR 把 `BOSS` 误识别成了 `8055`，并且没有稳定识别出 `留在此页`，只识别到了 `继续沟通`。

已处理：
- Boss 成功弹窗识别放宽：`已向BOSS发送消息`、`已向 Boss 发送消息`、`已向boss发送消息`，或同时出现 `已向` + `发送消息`，都算成功状态。
- 如果 OCR 没读到完整标题，但读到了 `Boss您好/职位非常感兴趣` 这类打招呼内容和 `继续沟通/留在此页` 按钮，也算成功弹窗。
- 点击、按键、等待类动作执行后，会立刻重新截图 + OCR 检查一次成功状态；如果发现成功弹窗，马上计入 `delivered` 并关闭弹窗。
- 关闭弹窗时优先点击 OCR 识别到的 `留在此页`；如果只识别到 `继续沟通`，则点击其左侧相对按钮区域，避免卡在当前弹窗。
- 事件日志新增 `postActionScreenshot`、`postActionVisibleTextSample`、`postActionSuccess`，便于复盘动作后的页面状态。

验证：
- `.\.venv\Scripts\python.exe -m py_compile scripts\mimo_ocr_agent.py` 通过。
- 用用户提供的真实 Boss 弹窗截图跑 EasyOCR：`boss_dialog=True`、`success_state=True`。
- 只识别到 `继续沟通` 时，兜底关闭逻辑会点击其左侧相对区域。

下一次让 Hermes 测试时重点看：
- `events[].outcome` 是否出现 `success_detected_after_action`。
- `delivered` 是否从 0 正确变为 1。
- 弹窗是否会自动关闭并继续滚动/进入下一份岗位。

---

## 2026-06-23 Codex 真实投递测试

测试命令核心参数：
- `--platform boss`
- `--keyword "Python实习生"`
- `--count 1`
- `--max-steps 3`
- `--auto-submit`
- `--no-open`
- `--resume-path "E:\学习\简历\五方向实习"`
- `--disable-text-match`

结果：
- 成功真实投递 1 个 Boss 岗位。
- 岗位：文远知行 `数据工程师实习生`，广州，300-400元/天。
- 返回结果：`success=true`、`delivered=1`、`needsUserAction=false`。
- 关键动作：Mimo 决策点击 `立即沟通`。
- 关键闭环：动作后重新截图识别到 `已向BOSS发送消息` 成功弹窗，并自动点击 `留在此页`。
- 关键 outcome：`executed;success_detected_after_action;clicked_留在此页`。

补充观察：
- 第一次通用目标测试跑到 5 分钟超时，原因不是弹窗卡住，而是 Mimo 对岗位筛选偏保守，选择继续切换/评估岗位，没有快速点击投递。
- 第二次把目标明确为“当前数据工程师实习生属于 Python/数据方向实习，看到立即沟通就点击”后，完整流程在约 69 秒内成功。
- 当前 `.env` 里的 DeepSeek key 不是 `sk-` 格式，因此本次真实投递先使用 `--disable-text-match`，只验证 Mimo 视觉闭环。

---

## 2026-06-23 DeepSeek 简历匹配硬门禁

背景：
- 真实投递不能只靠 Mimo 视觉判断按钮。
- 必须先让 DeepSeek 根据本地简历内容和当前岗位 OCR 文本判断是否匹配。
- 只有 DeepSeek 明确返回 `fit=apply`，且分数达到阈值时，程序才允许点击 `立即沟通/立即投递`。

已处理：
- DeepSeek 文本匹配提示词增加 `resume_match`，要求列出简历中匹配的技能/项目/经历，以及岗位要求中缺失或较弱的部分。
- 新增硬门禁 `text_match_submit_gate`：
  - `fit=apply` 且 `score_0_to_100 >= 70`：允许最终投递动作。
  - `fit=skip`：拦截投递，当前岗位计为跳过。
  - `fit=need_more_detail`：拦截投递，避免信息不足时误投。
  - DeepSeek key 缺失、报错、超时：进入 `need_user`，不会投递。
  - DeepSeek 被禁用：默认也会进入 `need_user`，除非显式加 `--allow-without-text-match` 做视觉链路测试。
- 事件日志新增 `textMatchGate`，可查看拦截/放行原因。
- 新增参数：
  - `--min-text-match-score`：默认 70。
  - `--allow-without-text-match`：仅用于调试 Mimo 视觉链路，真实投递不要用。

验证：
- `fit=apply, score=90`：放行。
- `fit=apply, score=60`：`blocked_text_match_score_below_threshold`。
- `fit=skip`：`blocked_text_match_skip`。
- DeepSeek 缺失：`need_user_text_match_missing`。
- DeepSeek 报错：`need_user_text_match_error`。

Hermes 下一次安全测试命令：
```powershell
cd "E:\新的投简历用的\npe_get_jobs_temp\npe_get_jobs-main"

$env:PYTHONIOENCODING='utf-8'
$env:TARGET_BROWSER='chrome'
$env:VISION_CURL_FALLBACK='true'
$env:DEEPSEEK_CURL_FALLBACK='true'

.\.venv\Scripts\python.exe scripts\mimo_ocr_agent.py `
  --platform boss `
  --keyword "Python实习生" `
  --objective "投递Python实习生方向；必须先根据本地Python方向简历判断岗位是否匹配；只在DeepSeek判断fit=apply时点击立即沟通/立即投递；不主动发送简历、不换微信、不换电话；遇到登录、验证码、安全验证、扫码登录就停下来。" `
  --count 1 `
  --max-steps 8 `
  --auto-submit `
  --initial-delay 8 `
  --action-delay 3 `
  --resume-path "E:\学习\简历\五方向实习" `
  --min-text-match-score 70
```

观察重点：
- 不要加 `--disable-text-match`。
- 不要加 `--allow-without-text-match`，除非只是调试 Mimo 视觉链路。
- 成功投递时，事件里应同时出现：
  - `textFitAnalysis.fit=apply`
  - `textMatchGate.allowed=true`
  - `outcome=executed;success_detected_after_action;clicked_留在此页`

---

## 2026-06-23 简历画像复用，避免每岗重复发送完整简历

背景：
- DeepSeek 仍然需要对每个岗位审查一次，因为每个岗位的 OCR 文本不同。
- 但不应该每次都发送完整简历，token 浪费太大。
- OpenAI-compatible `chat/completions` 通常是无状态接口；如果靠“历史 messages”保持上下文，实际请求仍要重复携带历史内容，token 不一定省。

已处理：
- 启动时先用完整简历调用 DeepSeek 一次，生成精简 `resume_profile`。
- 后续每个岗位的 DeepSeek 审查只发送：
  - `resume_profile`
  - 当前岗位 OCR 文本
  - 当前目标和输出 schema
- Mimo 视觉 prompt 也改为使用 `resume_profile`，不再每轮带完整简历摘要。
- `resume_profile` 会缓存在 `.cache/mimo_ocr_agent/resume_profiles/`，缓存键基于简历内容 hash、目标方向、模型和 profile 版本。
- 缓存目录 `.cache/` 已加入 `.gitignore`，不要上传。

安全策略：
- 如果 DeepSeek key 缺失或简历画像生成失败，程序在启动阶段返回 `need_user`，不会打开浏览器乱投。
- 已有缓存画像时可以复用缓存，但每个岗位的最终审查仍然需要 DeepSeek key。
- 真实投递仍然要求每个岗位 `textMatchGate.allowed=true`。

新增配置：
```env
RESUME_PROFILE_CACHE=true
RESUME_PROFILE_MAX_TOKENS=1200
TEXT_MATCH_MIN_SCORE=70
```

预期日志字段：
- `resumeProfileLoaded=true`
- `resumeProfileSource=deepseek` 或 `cache`
- 每个岗位事件里有 `textFitAnalysis`
- 最终投递事件里有 `textMatchGate.allowed=true`

---

## 2026-06-23 DeepSeek 门禁真实测试与右侧详情修正

真实测试结果：
- 运行目标：Boss `Python后端实习`，最多成功投递 1 个。
- 简历画像：已复用缓存，`resumeProfileSource=cache`。
- DeepSeek 每岗审查：已启用，`TEXT_LLM_MAX_TOKENS=4096`。
- 第一岗：DeepSeek 判定 `fit=skip`，分数 10，Mimo 按结论跳过。
- 第二步：程序完成一次真实投递，返回 `success=true`、`delivered=1`。

测试中发现的问题：
- Boss OCR 全屏文本同时包含左侧岗位列表和右侧岗位详情。
- 旧版 DeepSeek 审查把左侧列表里的岗位文本混入判断，可能出现“审查左侧列表 A，点击右侧详情 B”的风险。
- 本次真实投递后复盘截图确认：需要强制 DeepSeek 只看右侧当前岗位详情。

已修复：
- 新增 `current_job_detail_text()`，只提取 Boss 右侧当前岗位详情区域 OCR 文本。
- DeepSeek 每岗审查输入从全屏 `visible_text` 改为 `current_job_detail_text`。
- Prompt 明确要求：只判断右侧当前岗位详情，忽略左侧岗位列表。
- 事件日志新增 `currentJobTextSample`，方便核对 DeepSeek 审查的是哪一个岗位。
- `TEXT_LLM_MAX_TOKENS` 默认提高到 4096，避免 DeepSeek v4-flash 把 800 tokens 全用在 `reasoning_content` 后导致 `content` 为空。
- 若 DeepSeek 仍返回空 content，会记录 `finish_reason` 和 `reasoningLength`，并由 gate 拦截。

修复验证：
- 对真实投递前截图重新提取右侧详情：只包含 `初级Python开发工程师`，不再包含左侧第二个 `后端开发实习生 3-5K`。
- 修复后用同一右侧详情重新跑 DeepSeek：返回 `fit=skip`、分数 15、`textMatchGate.allowed=false`。
- 说明新逻辑会拦截该右侧岗位，不会再因左侧列表混入而误投。

---

## 2026-06-23 count=5 真实测试

本次目标：
- Boss `Python实习生`
- DeepSeek 简历画像门禁开启
- `--count 5`
- `TEXT_LLM_MAX_TOKENS=393216`
- `VISION_MAX_TOKENS=4096`

测试前修复：
- 岗位描述中出现 `验证码` 会误触发阻塞，例如“解决封账号、封IP、验证码等难点”。
- 已将阻塞判断改为页面级信号：`安全验证/人机验证/滑块/短信验证码/请输入验证码/扫码登录/异常访问` 等才阻塞。

max_tokens 结论：
- Mimo 视觉接口不接受 `VISION_MAX_TOKENS=1000000`，会返回 HTTP 400，因此视觉决策保持 `4096`。
- DeepSeek 接口也不接受 `TEXT_LLM_MAX_TOKENS=1000000`，错误提示有效范围为 `[1, 393216]`，因此 DeepSeek 使用最大合法值 `393216`。
- 简历画像生成也改为 `RESUME_PROFILE_MAX_TOKENS=393216`，避免 reasoning 吃光 token 后得到空画像。
- 空画像不会再被缓存或使用。

结果：
- 第一轮 `--count 5` 完成，耗时约 776 秒。
- 成功新增投递：2 个。
- DeepSeek 拦截/跳过：3 个。
- 成功投递的岗位：
  - `跨境电商数据分析师实习生`，DeepSeek `fit=apply`，分数 70。
  - `软件开发岗-实习生`，DeepSeek `fit=apply`，分数 80。
- 被拦截示例：
  - `数据采集与运维实习生`：缺爬虫/运维/Docker/Scrapy/Redis 等，分数 15。
  - `AI开发实习生`：偏机器学习/深度学习/大模型算法，分数 25。
  - `软件开发岗-实习生` 的中间两次判断曾给 55/65，低于阈值 70，被 gate 拦截。

补投尝试：
- 为补足剩余 3 个，继续从当前页面运行 `--count 3`。
- 因页面仍停在已沟通过的 `软件开发岗-实习生`，程序再次进入该岗位聊天页。
- 程序在聊天页停下，没有继续点 `发简历/换电话/换微信`。
- 补投新增成功：0。

当前结论：
- 真实投递链路可用，DeepSeek gate 能拦截不匹配岗位。
- `count` 当前更接近“尝试轮数”，不是“成功投递数直到满额”。
- 下一步应改状态机：
  - 已沟通过/进入聊天页时返回职位列表并选择下一个岗位，不重复当前岗位。
  - 将 `--count` 语义改为“目标成功投递数”，另加 `--max-candidates` 控制最多检查多少岗位。
  - 记录本轮已沟通过的岗位标题/公司，避免同一轮重复投递或重复进入聊天。

---

## 2026-06-23 聊天页自动退出

背景：
- 点击 `立即沟通` 后，Boss 有时不弹成功弹窗，而是直接进入聊天页。
- 旧逻辑在聊天页会停住，或者因为缺少岗位详情文本进入 `need_user_text_match_missing`。

已处理：
- 新增 `boss_chat_page_detected()`：识别 `搜索30天内的联系人/发简历/换电话/换微信/查看职位/按Enter键发送` 等聊天页信号。
- 新增 `boss_chat_delivery_detected()`：聊天页中出现 `送达/Boss您好/我对您发布的职位/你与该职位竞争者` 时，视为已完成打招呼。
- 新增 `leave_chat_page()`：聊天页不再停住，自动执行 `Alt+Left` 返回职位列表。
- `check_and_dismiss_success()` 现在支持：
  - 动作后进入成功弹窗：点击 `留在此页`。
  - 动作后进入聊天页且已送达：计入 `delivered`，然后退出聊天页。
  - 动作后误入聊天页但未检测到送达：退出聊天页，不继续操作聊天页。
- 主循环一开始如果发现当前就在聊天页，也会退出聊天页，不点击 `发简历/换电话/换微信`。

验证：
- 使用真实聊天页截图 `mimo_ocr_20260623_020912_390291.png`：
  - `boss_chat_page_detected=True`
  - `boss_chat_delivery_detected=True`
  - `check_and_dismiss_success()` dry-run 返回 `detected=true`、`dismissOutcome=chat_page;dry_run`
