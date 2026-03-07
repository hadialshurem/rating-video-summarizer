# Rating Video Summarizer 🤖🎥

![Banner](https://img.shields.io/badge/Status-Automated-success) ![GitHub Actions](https://img.shields.io/badge/cron-daily-blue)

A fully automated, serverless project that creates a static website summarizing the latest videos from the **"Rating"** YouTube channel using AI. 

## 🚀 How It Works
1. Every day at midnight (or manually), a **GitHub Action** triggers.
2. The `scripts/summarize.py` runs, fetching the latest 5 videos from the channel's RSS feed.
3. It downloads the Arabic or English transcripts.
4. It sends the transcripts to an **LLM API** (Google Gemini or OpenAI).
5. The LLM generates a structured HTML summary.
6. A new `index.html` is generated from a Jinja2 template and pushed back to the repo.
7. **GitHub Pages** serves the newly updated `index.html` instantly.

## 🛠️ Setup Instructions (For GitHub)

### 1. Push Code to GitHub
Create a new GitHub repository and push this folder's contents to it:
```bash
cd "/Users/bebo/Desktop/Local Ai/rating-video-summarizer"
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
git push -u origin main
```

### 2. Configure API Keys (GitHub Secrets)
To perform the AI summarization, the script needs an API Key. 
1. Go to your Repository's **Settings** > **Secrets and variables** > **Actions**.
2. Click **New repository secret**.
3. Name it `LLM_API_KEY` and paste your key.
   > **Note:** The script defaults to using OpenAI libraries. If you want to use Google Gemini, add `GEMINI_API_KEY` instead and the script will automatically switch.

### 3. Enable GitHub Pages
1. Go to **Settings** > **Pages**.
2. Under "Build and deployment", select **Deploy from a branch**.
3. Select `main` -> `/(root)` and click **Save**.

Your automated web application is now live! 

---

## 💻 Running Locally

You can run the generator manually on your Mac:
```bash
# 1. Create a virtual environment & install libraries
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Export your API Key
export LLM_API_KEY="sk-your-key-here"
# If testing with LM Studio locally:
# export LLM_BASE_URL="http://192.168.100.66:1234/v1"

# 3. Predict / Generate index.html
python scripts/summarize.py
```
Open `index.html` in your browser to see the results.
