# START HERE — Put an AI Assistant on YOUR Own Website

This guide is for absolute beginners (no GitHub, Vercel, or coding experience).
Follow the steps **in order**. At the end you will have:

- A chatbot that answers questions about **your** website.
- Running live on the internet at a free URL like `https://your-ai-bot.vercel.app`.
- Re-buildable any time your website changes.

---

## Understand the two pieces first

| Piece | What it is | Where it runs |
|---|---|---|
| **1. Knowledge pipeline** | A program that reads your website and turns it into a "knowledge file" (`vectors.json`). | On your computer (Python). |
| **2. The bot** | A small web app that answers questions using that knowledge file. | On the internet (Vercel, free). |

You run piece 1 on your computer. You deploy piece 2 once. Then anyone can chat with it.

---

## What you need before starting

Four free accounts and three free tools. Create the accounts at these exact links:

| Thing | Link | Cost |
|---|---|---|
| GitHub account | https://github.com/signup | Free |
| Vercel account | https://vercel.com/signup (sign up **with GitHub**) | Free |
| Google Gemini API key | https://aistudio.google.com/apikey | Free |
| Firecrawl API key | https://firecrawl.dev (sign up, copy key from dashboard) | Free tier |

Tools to install:

| Tool | Link | Note |
|---|---|---|
| Git | https://git-scm.com/downloads | Just click Next through the installer. |
| Python 3.11+ | https://www.python.org/downloads/ | **Tick "Add python.exe to PATH"** during install. |
| Node.js (LTS) | https://nodejs.org/ | Just click Next through the installer. |

> **Check they installed:** open a terminal (Windows: press `Win`, type `powershell`, Enter) and run each line:
> ```
> git --version
> python --version
> node --version
> ```
> Each must print a version number. If not, reinstall that tool.

---

# PART A — Get the code

### Step 1. Download the project

Easiest way (no Git needed):
1. Open https://github.com/GayatriSutar2004/aklm-prototype-
2. Click the green **Code** button → **Download ZIP**.
3. Right-click the ZIP → **Extract All** → extract to `C:\aklm` (remember this folder).

Or, if you prefer Git:
```
git clone https://github.com/GayatriSutar2004/aklm-prototype-.git C:\aklm
```

You now have a folder `C:\aklm` containing `run_pipeline.py`, `aklm_lib.py`, and a `bot_template` folder.

---

# PART B — Configure your keys

### Step 2. Create your `.env` file

1. In `C:\aklm`, find the file `.env.example`.
2. Make a copy of it and rename the copy to exactly `.env` (yes, no name before the dot).
3. Open `.env` with Notepad and fill it in:

```
GEMINI_API_KEY=paste_your_gemini_key_here
FIRECRAWL_API_KEY=paste_your_firecrawl_key_here
SITE_URL=https://YOUR-WEBSITE.com/
ADCETPORTAL_REPO=C:\my-ai-bot
```

- `SITE_URL` = your website's home page (the one the bot should learn).
- `ADCETPORTAL_REPO` = leave for now, you'll set it in Part E.
- Save the file.

> Never share `.env` or commit it to GitHub. It contains your secret keys.

---

# PART C — Build the knowledge on your computer

### Step 3. Install the Python libraries

In your terminal:
```
cd C:\aklm
python -m pip install -r requirements.txt
```
Wait until it finishes (it downloads a few packages).

### Step 4. Build the knowledge index

Run this (replace the URL with YOUR site):
```
python run_pipeline.py --mode full --url "https://YOUR-WEBSITE.com/" --query "What is this website about?"
```

What this does, step by step (you'll see these printed):
1. **CRAWL** — reads your website into text (uses Firecrawl).
2. **CHUNK** — splits the text into pieces.
3. **EMBED + STORE** — turns each piece into numbers with Gemini and saves them locally in Qdrant.
4. **QUERY TEST** — asks your test question and prints the answer.

If you see an answer at the end, **the knowledge pipeline works**. 🎉

> If it says "Firecrawl free credits exceeded", wait for the credits to reset (or use a different Firecrawl key).

---

# PART D — Create the bot's GitHub repository

### Step 5. Make an empty repository on GitHub

1. Go to https://github.com/new
2. Repository name: `my-ai-bot` (or anything).
3. Keep it **Public**. Do NOT tick "Add a README".
4. Click **Create repository**. Keep the page open.

### Step 6. Put the bot files on your computer

Copy the whole contents of `C:\aklm\bot_template\` into a new folder `C:\my-ai-bot\`.
So you end up with:
```
C:\my-ai-bot\api\ask.js
C:\my-ai-bot\api\vectors.json
C:\my-ai-bot\index.html
C:\my-ai-bot\vercel.json
C:\my-ai-bot\package.json
```

### Step 7. Upload the bot files to GitHub

In your terminal:
```
cd C:\my-ai-bot
git init
git add .
git commit -m "Add AI bot"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/my-ai-bot.git
git push -u origin main
```
When asked to log in, sign in to GitHub in the browser window that pops up.

> Replace `YOUR-USERNAME` with your GitHub username.

### Step 8. Fill the bot with YOUR website's knowledge

Now generate the knowledge file **directly into the bot repo** and push it:
```
cd C:\aklm
python run_pipeline.py --mode full --url "https://YOUR-WEBSITE.com/" --sync-live --repo "C:\my-ai-bot"
```
This writes `C:\my-ai-bot\api\vectors.json` and pushes it to GitHub automatically.

Also update `.env` so future runs remember it: set `ADCETPORTAL_REPO=C:\my-ai-bot`.

---

# PART E — Deploy the bot to the internet (Vercel)

### Step 9. Import the repo into Vercel

1. Go to https://vercel.com/new
2. Under **Import Git Repository**, find `my-ai-bot` and click **Import**.
3. Leave all settings as default. Click **Deploy**.
4. After ~1 minute you get a URL like `https://my-ai-bot.vercel.app`.

### Step 10. Add your Gemini key in Vercel (required)

1. In Vercel, open your project → **Settings** → **Environment Variables**.
2. Add:
   - Name: `GEMINI_API_KEY`
   - Value: your Gemini key
   - Environment: all (Production/Preview/Development)
3. Click **Save**.
4. Go to **Deployments** → top-right **⋯** on the latest → **Redeploy**.

### Step 11. Test it

Open your project URL, e.g. `https://my-ai-bot.vercel.app`.
Type a question about your website → you should get an answer with sources.

---

# PART F — Attach the bot to your app

You have two options. Pick whichever fits your app.

### Option 1 (easiest, works on ANY app) — embed with an iframe

Add this to any page of your app, replacing the URL with your bot's URL:
```html
<iframe
  src="https://my-ai-bot.vercel.app"
  style="width:100%;height:600px;border:0;border-radius:12px;"
  title="AI Assistant"></iframe>
```

### Option 2 — your own floating chat widget (calls the bot's API)

Add this snippet before the closing `</body>` of your app:
```html
<script>
  const AI_API = "https://my-ai-bot.vercel.app/api/ask";
  window.askAI = async function (question) {
    const res = await fetch(AI_API, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    const data = await res.json();
    return data.answer; // also available: data.sources
  };
</script>
```
Then wherever you want a chat box, call `askAI("your question")`.

> The bot endpoint already allows calls from other websites (CORS is on).

---

# PART G — Keep it updated when your website changes

Whenever you edit your website content, run ONE command:
```
cd C:\aklm
python run_pipeline.py --mode update --sync-live --repo "C:\my-ai-bot"
```
The pipeline:
- re-crawls your site,
- finds only the pages that actually changed,
- re-embeds **only** those (much cheaper),
- removes outdated knowledge,
- pushes the new `vectors.json`, and Vercel redeploys automatically.

Your bot is updated in ~1–2 minutes.

---

# Troubleshooting

| Problem | Fix |
|---|---|
| `python` not recognized | Reinstall Python and tick "Add python.exe to PATH", then reopen the terminal. |
| `ModuleNotFoundError: firecrawl` | Run `python -m pip install -r requirements.txt` again inside `C:\aklm`. |
| `FIRECRAWL_API_KEY not found` | Your `.env` file is missing or in the wrong folder (must be `C:\aklm\.env`). |
| Firecrawl credits exceeded | Wait for reset, or sign in to firecrawl.dev with another account/key. |
| Bot says "AI service temporarily unavailable" | Your `GEMINI_API_KEY` is missing/incorrect in Vercel → re-check Step 10 and redeploy. |
| Bot says "knowledge base is empty" | You didn't run Step 8, or the push failed. Re-run Step 8. |
| `git push` rejected / "fetch first" | Run `git -C "C:\my-ai-bot" pull --rebase origin main` then `git -C "C:\my-ai-bot" push`. |
| Answer is wrong/old | Re-run Part G to refresh, then hard-refresh the page (`Ctrl+F5`). |
| Vercel build error | Make sure `api\ask.js`, `api\vectors.json`, `vercel.json`, `package.json` are all present. |

---

## Quick reference (the two commands that matter)

```bash
# Build/refresh knowledge + deploy it to the bot repo:
cd C:\aklm
python run_pipeline.py --mode update --sync-live --repo "C:\my-ai-bot"

# First time only (full rebuild):
python run_pipeline.py --mode full --url "https://YOUR-WEBSITE.com/" --sync-live --repo "C:\my-ai-bot"
```
