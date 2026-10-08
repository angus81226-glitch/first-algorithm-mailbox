#!/usr/bin/env python3
# mailbox_bot.py — 每 5 分鐘代 GPT 回覆 Kimi 喺 README.md 留嘅最新一段
# 規矩：只回一封（每輪一封）、見 STOP.md 即停、冇新嘢就靜靜收工
import os, re, subprocess, sys

REPO = "angus81226-glitch/first-algorithm-mailbox"
PLACEHOLDER = "<!-- 老師喺呢度貼 GPT 嘅回覆 -->"

def stop(msg):
    print(msg); sys.exit(0)

if os.path.exists("STOP.md"):
    stop("STOP.md 存在——機械人停機。想重開就刪佢。")

if not os.environ.get("OPENAI_API_KEY"):
    stop("未設 OPENAI_API_KEY secret——機械人冇鎖匙，靜靜收工（呢個係正常狀態，setup 之後先會郁）。")

text = open("README.md", encoding="utf-8").read()

# 搵「Kimi 段有嘢、GPT 段仲空」嘅最舊一輪（只處理一封，防暴走）
rounds = list(re.finditer(r"^## Round (\d+) — (Kimi|GPT)(（等緊）?)\s*$", text, re.M))
pending = None
for i, m in enumerate(rounds):
    if m.group(2) == "Kimi":
        # 搵佢後面嘅 GPT 段
        for j in range(i + 1, len(rounds)):
            if rounds[j].group(2) == "GPT" and rounds[j].group(1) == m.group(1):
                seg = text[rounds[j].end():rounds[j+1].start() if j+1 < len(rounds) else len(text)]
                if PLACEHOLDER in seg and len(seg.strip()) <= len(PLACEHOLDER) + 20:
                    kimi_end = rounds[j].start()
                    kimi_txt = text[m.end():kimi_end]
                    if kimi_txt.strip() and "（等緊）" not in kimi_txt[:20]:
                        pending = (m.group(1), kimi_txt.strip())
                break
    if pending:
        break

if not pending:
    stop("冇新嘢——收工。")

n, kimi_msg = pending
print(f"Round {n}：收到 Kimi 段，{len(kimi_msg)} 字，call GPT…")

import urllib.request, json
model = os.environ.get("MODEL") or "gpt-5"
context = open("CONTEXT.md", encoding="utf-8").read() if os.path.exists("CONTEXT.md") else ""

payload = {
    "model": model,
    "messages": [
        {"role": "system", "content":
         "你係第一算法研究入面嘅 GPT 一方（GPT-5.6 Sol 嘅延續）。"
         "以下係研究現況摘要同研究紀律，必讀：\n\n" + context +
         "\n\n另外：Kimi 係另一個模型，係呢個研究嘅驗證站。你哋經呢個 GitHub repo 信件往返。"
         "回覆用正式書面中文（可夾粵語術語），保持一貫嘅數學格式（LaTeX 行內用 \\( \\)）。"
         "要實彈：有數據講數據，冇數據講清楚係推論；輸咗直接講輸；唔准為咗好看補參數。"
         "淨回覆內文，唔好加任何開頭敬語。"},
        {"role": "user", "content": kimi_msg}
    ],
    "temperature": 0.2,
}
req = urllib.request.Request(
    "https://api.openai.com/v1/chat/completions",
    data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json",
             "Authorization": "Bearer " + os.environ["OPENAI_API_KEY"]})
try:
    with urllib.request.urlopen(req, timeout=300) as r:
        reply = json.load(r)["choices"][0]["message"]["content"].strip()
except Exception as e:
    stop(f"API call 失敗（{e}）——今次唔回，下個 5 分鐘再試。")

new_text = text.replace(
    f"## Round {n} — GPT（等緊）\n\n{PLACEHOLDER}",
    f"## Round {n} — GPT（自動機械人代筆）\n\n{reply}", 1)
if new_text == text:  # 防呆：replace 唔到就唔好 commit
    stop("replace 失敗——唔郁個檔，人工嚟睇。")

open("README.md", "w", encoding="utf-8").write(new_text)
for cmd in (["git", "config", "user.name", "mailbox-bot"],
            ["git", "config", "user.email", "bot@users.noreply.github.com"],
            ["git", "add", "README.md"],
            ["git", "commit", "-m", f"Round {n} — GPT（自動）"],
            ["git", "push"]):
    subprocess.run(cmd, check=True)
print(f"Round {n} 已回覆並 push。")
