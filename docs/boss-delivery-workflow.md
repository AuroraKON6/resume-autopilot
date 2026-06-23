# Boss Delivery Workflow

This workflow is based on `E:\学习\boss的主页面.docx`.

## Safety Boundary

The agent must stop for login, QR login, captcha, SMS code, slider verification, abnormal access, or any security check. It must not automate those steps.

Click actions use an element `box` instead of a fixed global point so the same workflow can adapt to different screen sizes and page layouts. The click executor chooses a safe point inside the returned box for UI reliability.

The resume is matching context only. On BOSS the default delivery action is greeting/contacting the recruiter through `立即沟通` / `立即投递`; the agent must not upload, edit, select, or send a resume file unless the user explicitly asks.

## Workflow

1. Logged-in check
   - Signals: username/avatar/messages/resume are visible.
   - If login, QR login, captcha, verification, or abnormal access is visible, return `need_user`.

2. Search
   - Find the Boss search input.
   - Type the target role/company keyword if needed.
   - Click the `搜索` button.

3. Job list and detail
   - Use the left job-card list and right job-detail panel.
   - Read title, tags, city, salary, experience, education, description, and requirements.
   - Send extracted text to the job-fit prompt.

4. Match decision
   - Apply only when the job clearly matches the user's objective.
   - If the user asks for internship/实习, require clear internship/campus/应届 signals.
   - If insufficient detail is visible, click `查看更多信息` or scroll the detail panel.
   - If not a fit, click the next left-side job card.

5. Apply/contact
   - If the job is a fit, click `立即沟通`.
   - Return a `box` covering the visible `立即沟通` button.
   - Set `is_final_submit=true`.

6. Confirmation dialog
   - If dialog says `已向BOSS发送消息`, the job is delivered.
   - Prefer `留在此页` when more jobs remain.
   - Use `继续沟通` only when the objective explicitly asks to enter chat.

7. Chat page
   - Do not send a custom HR message unless the objective provides one.
   - Do not click `发简历`, `换电话`, or `换微信` unless explicitly requested.
   - If already in the chat page after a successful contact, mark current job done.

8. Next job
   - Return to or remain on the search/detail page.
   - Click the next left-side job card.

9. City switch
   - Use city controls only when the objective explicitly requests another city.
   - Boss daily delivery volume should remain user-configured and conservative.

## Company Target Mode

Use this mode only when the user specifies a company, via `--target-company` or `--search-mode company`.

1. Search/open the target company
   - Search input can accept either a role or a company.
   - If `--target-company` is present, use that company name as the search query.
   - Click the `公司`/company result rather than unrelated job cards.

2. Company page
   - Signals: `公司简介`, `招聘职位`, `在招职位`, `职位类型`, `工作城市`, `工作经验`, `学历要求`, `薪资待遇`.
   - Click `招聘职位`; if the page shows `查看全部...职位`, click it before scanning.
   - Apply filters only when the objective asks for them.

3. Company job list
   - Evaluate only jobs under that company.
   - Use the same DeepSeek review by default.
   - If the job matches, click `立即沟通`.

## Campus And Internship Area

Boss update from `docx/boss的主页面.docx`:

- `校园·海归` is useful when the resume/user objective implies current student, internship, campus hire, or no-experience work.
- For `Python实习生` or other internship targets, choose the `实习` tab instead of staying on `校招`.
- A card that only says `应届生` should be treated as graduate-only unless it also shows `在校`, `实习`, or another current-student/internship signal.
- Cards showing `在校/应届` are acceptable internship/current-student signals, but still need title/skill/city matching.
- When scanning Boss lists, scroll inside the left-side job-card area. At the end of the visible list/page, use `查看更多` or the next-page control only after visible cards are exhausted.
- After `已向BOSS发送消息`, click `留在此页` quickly when continuing to the next job; do not enter chat unless explicitly requested.
- Boss is the exception to the current-tab-close rule: when the success dialog offers `留在此页`, click `留在此页` instead of closing the browser tab.

## Fast Mode

Enable with `--fast-mode`. This mode is faster because it judges visible OCR card text before opening long detail pages. In release usage, the match decision is still made by the configured API AI (`TEXT_LLM_API_KEY`/`DEEPSEEK_API_KEY` compatible endpoint), not by Hermes or local hard-coded rules.

Boss fast-mode rules from `docx/快速模式详细以boss直聘为例.docx`:

- Use visible card/detail OCR text: title, tags, salary, city, education, and job type.
- Ignore the HR name/avatar area.
- If the target is `python实习`, require explicit `Python`/target direction plus `实习`/`Intern` or `在校`.
- `26届校招` or `应届生` alone is not enough for an internship target.
- High monthly 校招 salary such as `12-18K·14薪` without `实习`/`在校` should be skipped for an internship target.
- If the user specifies a city, skip cards whose visible city does not match.
- `本科` is acceptable for bachelor or above; `硕士`/`研究生`/`博士` should be skipped when the candidate is bachelor.
- For Python/technical targets, click `技术` under `职位类型` when visible before scanning.
- Scroll inside the job-card list area, not the unrelated right-side/detail area.
- At the end of a page, use the visible right-arrow/next-page control.

## Multimodal Vision Prompt

```text
You are controlling the user's own desktop browser to help with a job application.
Make one safe next-step decision from OCR text and screenshot.

Rules:
- Return one JSON object only. No markdown.
- For click actions, prefer returning a box object for the visible UI element:
  {"x1": int, "y1": int, "x2": int, "y2": int}.
- The box must cover the actual button, job card, input, or control seen on screen.
- Use x/y only if a box is impossible.
- If captcha, slider, SMS code, QR login, login page, or security check is visible, choose need_user.
- On BOSS, 立即沟通 is an application/contact action; only click it when the current job is a clear match.
- On BOSS campus pages, if the objective asks for internship/Python实习, select 实习 under 校园·海归; 校招 or 应届生 alone is not enough unless the user explicitly asks for campus hire/应届 jobs.
- On BOSS fast mode, require 实习/Intern or 在校 for internship targets. Do not treat 26届校招 or 应届生 alone as internship.
- On BOSS, if a dialog says 已向BOSS发送消息 with 留在此页/继续沟通, the current job is already delivered.
- When skipping a BOSS job, click the next job card in the left list and explain the mismatch.
- Do not send a custom HR message unless the objective explicitly provides one.
- Do not invent success. Use done only when the current job is already applied or the objective is complete.

JSON schema:
{
  "action": "click|scroll|type|press|hotkey|wait|done|need_user",
  "box": {"x1": 0, "y1": 0, "x2": 0, "y2": 0},
  "x": 0,
  "y": 0,
  "text": "visible target text if any",
  "value": "text to type, key name, or hotkey list",
  "direction": "up|down",
  "is_final_submit": false,
  "state": "workflow state name",
  "match_score": 0,
  "reason": "short reason",
  "expect": "what should change after the action"
}
```

## Job-Fit Text Prompt

```text
Read the extracted job title, tags, description, requirements, city, salary,
experience, and education. Judge whether this job should be applied to for
the user's objective.

Be conservative:
- Apply only when the visible text clearly matches the target keyword and
  resume intent.
- If the objective mentions internship, intern, 实习, 应届, or campus, require
  clear internship/campus/应届 signals.
- Skip jobs with obvious mismatch in city, seniority, education, salary,
  full-time/internship type, or required tech stack.
- If important evidence is missing, request more detail or scroll instead of
  applying.

Return:
{
  "fit": "apply|skip|need_more_detail",
  "score_0_to_100": 0,
  "evidence": ["visible evidence"],
  "missing_or_risk": ["risk"],
  "next_action": "click_apply|click_next_job|scroll_detail|need_user"
}
```
