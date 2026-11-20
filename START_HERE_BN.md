# SentinelGate AI MVP — শুরু করার বাংলা গাইড

## ১) ZIP Extract করে Claude Code-এ Open করো

Project Folder: `sentinelgate-ai-mvp`

Claude Code-এ এই Folder Open করো। প্রথমে `CLAUDE.md` এবং `docs/CLAUDE-CODE-FIRST-PROMPT.md` পড়তে বলো।

## ২) Backend চালাও

প্রথম Terminal:

```bash
cd sentinelgate-ai-mvp/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

API পরীক্ষা: http://127.0.0.1:8000/api/health

## ৩) Frontend চালাও

দ্বিতীয় Terminal:

```bash
cd sentinelgate-ai-mvp/frontend
npm install
cp .env.example .env
npm run dev
```

Dashboard: http://localhost:5173

Node.js-এর Version আগে পরীক্ষা করো:

```bash
node --version
npm --version
```

Vite 8-এর জন্য Node.js 20.19+ অথবা 22.12+ প্রয়োজন।

## ৪) Demo পরীক্ষা

Dashboard-এ চারটি Scenario আছে:

- Trusted invoice read → ALLOW
- Indirect prompt injection → BLOCK
- Unauthorized database action → BLOCK
- Unknown provenance → REVIEW

BLOCK এবং REVIEW হলে Tool Execute হবে না। ALLOW হলেও শুধু Mock/Demo Data দেখাবে। বাস্তব Email বা Database ব্যবহার করে না।

## ৫) গুরুত্বপূর্ণ সতর্কতা

Default MVP-তে SLM চালু নেই; Rule-based Heuristic Scanner ব্যবহার হয়। Dashboard-এ এটি স্পষ্টভাবে দেখায়। Optional Transformer Classifier চালু করার নিয়ম `README.md`-এর Section 3-এ রয়েছে। এই Prototype-কে Production Security Product হিসেবে উপস্থাপন করবে না।

## ৬) Claude Code-কে প্রথমে যে Prompt দেবে

`docs/CLAUDE-CODE-FIRST-PROMPT.md`-এর নির্দেশনা ব্যবহার করো। Claude-কে আগে Project inspect, Backend tests, Frontend build, এবং চারটি Demo scenario verify করতে বলবে। নতুন করে Project বা UI বানাতে বলবে না।
