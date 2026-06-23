# OCR Delivery Release Test Plan

This checklist is for landing the OCR + API-AI delivery agent without relying on real applications during automated tests.

## 0. Safety Rules

- Do not run real delivery unless the user explicitly approves the platform, keyword, count, and resume context.
- Automated tests must not handle login, QR code, SMS, captcha, slider, or security challenges.
- Release fast mode must use API AI judgement by default:
  - `FAST_MATCH_USE_API_AI=true`
  - `FAST_MATCH_LOCAL_FALLBACK=false`
- Local code may enforce safety gates, but must not hard-code whether a job matches.

## 1. Offline Must-Pass Tests

Run:

```powershell
python -m unittest tests.test_mimo_ocr_agent_offline -v
python scripts\mimo_ocr_agent.py --help
```

Expected:

- All offline tests pass.
- CLI help prints without crashing.
- No API request, browser click, OCR capture, or real delivery happens.

Covered cases:

- Mimo bad actions: `null`, `None`, `noop`, unknown action.
- Mimo aliases: `tap -> click`, `move -> hover`, `back -> Alt+Left`.
- Final delivery gate blocks apply/contact unless text fit is `apply` and score passes.
- Hover does not count as final delivery.
- Boss success uses `留在此页`; Liepin/51job/Zhilian close current tab.
- Login/captcha/security states block.
- Fast mode defaults to API AI and local fallback is off.
- Education matching is general, not hard-coded to `大专`.
- Four platform workflow signals are present.

## 2. API Configuration Smoke Test

Use harmless dry-run:

```powershell
python scripts\mimo_ocr_agent.py --platform liepin --keyword "市场营销实习" --fast-mode --dry-run --count 1 --max-steps 2 --no-open
```

Expected:

- If API keys are missing, program reports `need_user` / configuration error, not a crash.
- If API keys exist, DeepSeek/API-AI returns structured job-fit JSON.
- Mimo action must be one of allowed actions or safely normalized.

## 3. Visual Decision Dry-Run

With the target site already open and logged in:

```powershell
python scripts\mimo_ocr_agent.py --platform liepin --keyword "市场营销实习" --fast-mode --dry-run --count 1 --max-steps 5
```

Expected:

- OCR text is captured.
- API AI judges visible card/detail text.
- Mimo does not click final contact/apply in dry-run.
- If Mimo returns invalid action, parser turns it into `wait` or `need_user`.

## 4. Single Real Delivery Test

Only after user approval:

```powershell
python scripts\mimo_ocr_agent.py --platform liepin --keyword "市场营销实习" --fast-mode --auto-submit --count 1 --max-steps 8
```

Expected:

- One approved matching job is contacted/applied.
- Non-matching jobs are skipped.
- After success:
  - Boss clicks `留在此页`.
  - Liepin/51job/Zhilian close the current Chrome tab (`X` or `Ctrl+W`), not previous page content.

## 5. Continuous Delivery Test

Only after single delivery passes:

```powershell
python scripts\mimo_ocr_agent.py --platform boss --keyword "Python实习生" --fast-mode --auto-submit --count 5 --max-steps 10
```

Expected:

- Success count increases accurately.
- Skip count increases for mismatches.
- Agent does not enter chat tools such as `发简历`, `换电话`, `换微信`, `交换手机号`, or `交换微信号`.
- Agent recovers from success pages/tabs and continues to next job.

## 6. Platform-Specific Cases

- Boss:
  - Normal search/detail page.
  - `已向BOSS发送消息` dialog with `留在此页`.
  - On the `已向BOSS发送消息` dialog, the agent must click `留在此页` only. It must never click `继续沟通`, because that enters chat and can loop.
  - `校园·海归` page, internship tab.
  - Company target mode.
  - When skipping or searching more jobs, the mouse wheel must scroll over the left job-card list. It must not refresh the page, scroll the browser toolbar/header, or scroll only the right detail panel.
- Liepin:
  - Search list with hidden `聊一聊` that appears after hover.
  - Detail page.
  - Campus project detail page with `校招介绍`, `校招职位`, `职位筛选`, `到底了`.
  - Current tab close after delivery.
- 51job:
  - List-card `投递` with enough OCR text.
  - Detail `立即投递`.
  - Confirmation dialog.
  - Success/app page closes current tab.
- Zhilian:
  - Search results must open detail first.
  - Detail `立即投递`.
  - Success/`已投递` closes current tab.

## 7. Failure Cases To Verify

- Missing text API key.
- Missing vision API key.
- Vision API timeout.
- Text API timeout.
- Mimo returns `action: null`.
- Mimo returns unsupported action.
- Boss success dialog loops by clicking `继续沟通` instead of `留在此页`.
- OCR returns too little text.
- Captcha/login/security page appears.
- Browser focus fails.
- Boss scroll action refreshes the page or does not move the left job-card list.
- Apply/contact button hidden after hover.
- Success count not incrementing.
- Current tab close fails or closes wrong tab.
