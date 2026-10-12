# MailMind
AI email digest: Gmail (read-only) + Groq. Shows priority, action, deadline,
category, a daily briefing, charts, and CSV export.

## Setup
1. pip install -r requirements.txt
2. Create a Google Cloud OAuth "Desktop app" client, enable the Gmail API,
   and save it as credentials.json in the project folder.
3. Copy .env.example to .env and add your GROQ_API_KEY.
4. streamlit run app.py

Privacy: email text (trimmed) is sent to Groq for analysis. Gmail access is
read-only. Credentials and tokens stay local and are never committed.
