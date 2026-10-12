
import os
import re
import base64
import html
from email.utils import parseaddr

import streamlit as st
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# =========================================================
# CONFIGURATION
# =========================================================
st.set_page_config(
    page_title="MailMind | Email Digest",
    page_icon="📩",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_FILE = os.path.join(BASE_DIR, "credentials.json")
TOKEN_FILE = os.path.join(BASE_DIR, "token.json")

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


# =========================================================
# PROFESSIONAL STYLING
# =========================================================
st.markdown(
    """
    <style>
    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1250px;
    }
    .hero {
        padding: 1.5rem;
        border-radius: 18px;
        background: linear-gradient(120deg, #172554, #1d4ed8);
        color: white;
        margin-bottom: 1.5rem;
    }
    .hero h1 {
        color: white;
        margin-bottom: 0.35rem;
    }
    .hero p {
        color: #dbeafe;
        margin-bottom: 0;
    }
    .muted {
        color: #64748b;
        font-size: 0.9rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# EMAIL UTILITIES
# =========================================================
def decode_body(payload):
    """Extract readable text from a Gmail message payload."""
    plain_parts = []
    html_parts = []

    def walk(part):
        mime_type = part.get("mimeType", "")
        data = part.get("body", {}).get("data")

        if data:
            try:
                decoded = base64.urlsafe_b64decode(
                    data + "=" * (-len(data) % 4)
                ).decode("utf-8", errors="replace")

                if mime_type == "text/plain":
                    plain_parts.append(decoded)
                elif mime_type == "text/html":
                    html_parts.append(decoded)
            except (ValueError, UnicodeError):
                pass

        for child in part.get("parts", []):
            walk(child)

    walk(payload)

    if plain_parts:
        return "\n".join(plain_parts).strip()

    if html_parts:
        raw_html = "\n".join(html_parts)
        raw_html = re.sub(
            r"(?i)<\s*(br|/p|/div|/li|/tr)\b[^>]*>",
            "\n",
            raw_html,
        )
        text = re.sub(r"<[^>]+>", " ", raw_html)
        return html.unescape(re.sub(r"\s+", " ", text)).strip()

    return ""


def get_header(headers, name):
    for header in headers:
        if header.get("name", "").lower() == name.lower():
            return header.get("value", "")
    return ""


def parse_message(message):
    """Convert a Gmail API message into a simple dictionary."""
    payload = message.get("payload", {})
    headers = payload.get("headers", [])

    sender_raw = get_header(headers, "From")
    sender_name, sender_address = parseaddr(sender_raw)

    return {
        "id": message.get("id", ""),
        "thread_id": message.get("threadId", ""),
        "subject": get_header(headers, "Subject") or "(No subject)",
        "sender": sender_name or sender_address or sender_raw or "Unknown sender",
        "sender_address": sender_address,
        "date": get_header(headers, "Date") or "Date unavailable",
        "snippet": message.get("snippet", ""),
        "body": decode_body(payload),
    }


# =========================================================
# RULE-BASED DIGEST ANALYSIS
# =========================================================
def analyze_email(subject, body):
    text = f"{subject} {body}".strip()
    lower = text.lower()

    high_words = [
        "urgent",
        "immediately",
        "asap",
        "final notice",
        "overdue",
        "late submissions will not be accepted",
        "deadline has passed",
        "action required immediately",
        "account suspended",
        "payment overdue",
    ]

    medium_words = [
        "deadline",
        "submit",
        "submission",
        "tomorrow",
        "meeting",
        "action required",
        "by monday",
        "by tuesday",
        "by wednesday",
        "by thursday",
        "by friday",
        "by saturday",
        "by sunday",
        "please respond",
        "please confirm",
    ]

    if any(word in lower for word in high_words):
        priority = "High"
    elif any(word in lower for word in medium_words):
        priority = "Medium"
    else:
        priority = "Low"

    # Find a likely action sentence.
    sentences = [
        s.strip()
        for s in re.split(r"(?<=[.!?])\s+|\n+", body.strip())
        if s.strip()
    ]

    action_words = [
        "submit", "send", "complete", "upload", "review",
        "reply", "attend", "confirm", "prepare", "finish",
        "respond", "register", "pay", "provide", "bring",
        "schedule", "sign", "approve", "call", "contact",
        "please do", "make sure", "remember to",
    ]

    action = "No clear action detected"

    for sentence in sentences:
        sentence_lower = sentence.lower()
        if any(word in sentence_lower for word in action_words):
            action = sentence
            break

    # Find a likely deadline phrase.
    deadline_patterns = [
        r"\b(?:by|before|on)\s+"
        r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)"
        r"(?:,?\s+\d{1,2}(?:st|nd|rd|th)?)?"
        r"(?:\s+at\s+\d{1,2}(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?)?)?",

        r"\b(?:today|tomorrow|tonight)\b"
        r"(?:\s+at\s+\d{1,2}(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?)?)?",

        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",

        r"\b(?:by|before)\s+\d{1,2}(?::\d{2})?\s*(?:a\.?m\.?|p\.?m\.?)\b",
    ]

    deadline = "Not detected"

    for pattern in deadline_patterns:
        match = re.search(pattern, body, re.IGNORECASE)
        if match:
            deadline = match.group(0)
            break

    # An extractive preview, not a semantic AI summary.
    summary_sentences = sentences[:2]
    summary = " ".join(summary_sentences)

    if not summary:
        summary = "No readable email content available."

    if len(summary) > 280:
        summary = summary[:277].rsplit(" ", 1)[0] + "..."

    return {
        "priority": priority,
        "action": action,
        "deadline": deadline,
        "summary": summary,
    }


# =========================================================
# GMAIL AUTHENTICATION
# =========================================================
def get_google_credentials():
    """Load saved credentials or start Desktop OAuth."""
    creds = None

    if not os.path.exists(CREDENTIALS_FILE):
        raise FileNotFoundError(
            "credentials.json was not found in the project folder."
        )

    if os.path.exists(TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(
                TOKEN_FILE, SCOPES
            )
        except (ValueError, OSError):
            creds = None

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        # Desktop app credentials are required for this flow.
        flow = InstalledAppFlow.from_client_secrets_file(
            CREDENTIALS_FILE, SCOPES
        )
        creds = flow.run_local_server(
            port=0,
            open_browser=True,
            access_type="offline",
            prompt="consent",
        )

    with open(TOKEN_FILE, "w", encoding="utf-8") as token_file:
        token_file.write(creds.to_json())

    return creds


def fetch_recent_emails(max_results=20):
    """Read recent Gmail messages. Does not modify the inbox."""
    creds = get_google_credentials()
    service = build("gmail", "v1", credentials=creds, cache_discovery=False)

    results = service.users().messages().list(
        userId="me",
        maxResults=max_results,
        labelIds=["INBOX"],
    ).execute()

    messages = results.get("messages", [])
    emails = []

    for item in messages:
        full_message = service.users().messages().get(
            userId="me",
            id=item["id"],
            format="full",
        ).execute()

        emails.append(parse_message(full_message))

    return emails


# =========================================================
# SESSION STATE
# =========================================================
if "emails" not in st.session_state:
    st.session_state.emails = []

if "gmail_connected" not in st.session_state:
    st.session_state.gmail_connected = False

if "gmail_error" not in st.session_state:
    st.session_state.gmail_error = ""


# =========================================================
# SIDEBAR
# =========================================================
with st.sidebar:
    st.markdown("## 📩 MailMind")
    st.caption("Your email, simplified.")
    st.divider()

    st.markdown("### Gmail connection")

    if st.session_state.gmail_connected:
        st.success("Gmail connected")
    else:
        st.info("Gmail not connected")

    connect_clicked = st.button(
        "🔐 Connect / Refresh Gmail",
        type="primary",
        use_container_width=True,
    )

    st.caption(
        "Permission requested: read-only. "
        "The app cannot send, delete, or modify your emails."
    )

    st.divider()
    st.markdown("### Inbox filters")

    priority_filter = st.selectbox(
        "Priority",
        ["All", "High", "Medium", "Low"],
    )

    search_text = st.text_input(
        "Search emails",
        placeholder="Subject or sender...",
    )

    max_emails = st.select_slider(
        "Emails to fetch",
        options=[10, 20, 30, 50],
        value=20,
    )

    st.divider()
    st.caption("MailMind • Local prototype")


# =========================================================
# CONNECT / FETCH GMAIL
# =========================================================
if connect_clicked:
    if not os.path.exists(CREDENTIALS_FILE):
        st.session_state.gmail_error = (
            f"Missing credentials.json. Expected location: {CREDENTIALS_FILE}"
        )
        st.error(st.session_state.gmail_error)
    else:
        try:
            with st.spinner(
                "Opening Google authorization if needed, then reading inbox..."
            ):
                fetched = fetch_recent_emails(max_emails)

            st.session_state.emails = fetched
            st.session_state.gmail_connected = True
            st.session_state.gmail_error = ""
            st.success(f"Loaded {len(fetched)} recent inbox emails.")
        except FileNotFoundError as exc:
            st.session_state.gmail_error = str(exc)
            st.error(str(exc))
        except HttpError as exc:
            st.session_state.gmail_error = (
                "Gmail API returned an error. Check that the API is enabled "
                "and your Google account is an OAuth test user if the app "
                "is still in testing mode."
            )
            st.error(st.session_state.gmail_error)
            with st.expander("Technical details"):
                st.code(str(exc))
        except Exception as exc:
            st.session_state.gmail_error = (
                "Could not connect to Gmail. Check your OAuth configuration, "
                "internet connection, and credentials file."
            )
            st.error(st.session_state.gmail_error)
            with st.expander("Technical details"):
                st.code(str(exc))


# =========================================================
# HEADER
# =========================================================
st.markdown(
    """
    <div class="hero">
        <h1>MailMind</h1>
        <p>Your personal email digest — important messages, actions, and
        deadlines in one place.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

left, right = st.columns([3, 1])

with left:
    st.markdown("### Your email overview")
    st.markdown(
        '<p class="muted">Rule-based analysis • No OpenAI API key required</p>',
        unsafe_allow_html=True,
    )

with right:
    st.metric(
        "Emails loaded",
        len(st.session_state.emails),
    )


# =========================================================
# EMAIL DASHBOARD
# =========================================================
if not st.session_state.emails:
    st.markdown("### Welcome!")
    st.write(
        "Connect Gmail from the sidebar to load recent inbox messages. "
        "Your first authorization opens a Google sign-in page."
    )

    st.markdown("#### Or preview the dashboard")
    if st.button("Load sample emails"):
        st.session_state.emails = [
            {
                "id": "demo-1",
                "thread_id": "demo-1",
                "subject": "Software Engineering Assignment",
                "sender": "Professor",
                "sender_address": "professor@example.com",
                "date": "Demo message",
                "snippet": "Submit your assignment by Friday at 5 PM.",
                "body": (
                    "Dear students,\n"
                    "Submit your Software Engineering assignment by Friday "
                    "at 5 PM through the college portal. The document must "
                    "be uploaded as a PDF. Late submissions will not be accepted."
                ),
            },
            {
                "id": "demo-2",
                "thread_id": "demo-2",
                "subject": "Team meeting tomorrow",
                "sender": "Project Team",
                "sender_address": "team@example.com",
                "date": "Demo message",
                "snippet": "Please attend tomorrow's project meeting.",
                "body": (
                    "Please attend tomorrow's project meeting and prepare "
                    "your progress update."
                ),
            },
            {
                "id": "demo-3",
                "thread_id": "demo-3",
                "subject": "Weekly newsletter",
                "sender": "Newsletter",
                "sender_address": "news@example.com",
                "date": "Demo message",
                "snippet": "Here are this week's updates.",
                "body": "Here are this week's updates and articles to read.",
            },
        ]
        st.rerun()

else:
    analysed_emails = []

    for email_item in st.session_state.emails:
        analysis = analyze_email(
            email_item["subject"],
            email_item["body"] or email_item["snippet"],
        )

        analysed_emails.append({
            **email_item,
            **analysis,
        })

    # Apply filters
    filtered_emails = []

    for email_item in analysed_emails:
        if (
            priority_filter != "All"
            and email_item["priority"] != priority_filter
        ):
            continue

        searchable = (
            email_item["subject"] + " " + email_item["sender"]
        ).lower()

        if search_text.strip() and search_text.lower() not in searchable:
            continue

        filtered_emails.append(email_item)

    high_count = sum(
        item["priority"] == "High" for item in analysed_emails
    )
    medium_count = sum(
        item["priority"] == "Medium" for item in analysed_emails
    )
    action_count = sum(
        item["action"] != "No clear action detected"
        for item in analysed_emails
    )

    metric1, metric2, metric3 = st.columns(3)
    metric1.metric("🔴 High priority", high_count)
    metric2.metric("🟠 Medium priority", medium_count)
    metric3.metric("✅ Possible actions", action_count)

    st.divider()
    st.markdown(f"### Inbox digest ({len(filtered_emails)} messages)")

    if not filtered_emails:
        st.info("No emails match your current filters.")

    for index, item in enumerate(filtered_emails):
        priority = item["priority"]

        if priority == "High":
            priority_icon = "🔴"
        elif priority == "Medium":
            priority_icon = "🟠"
        else:
            priority_icon = "🟢"

        with st.container(border=True):
            title_col, badge_col = st.columns([4, 1])

            with title_col:
                st.markdown(f"**{item['subject']}**")
                st.caption(
                    f"From: {item['sender']}  •  {item['date']}"
                )

            with badge_col:
                st.markdown(f"**{priority_icon} {priority}**")

            st.markdown("**Digest preview**")
            st.write(item["summary"])

            action_col, deadline_col = st.columns(2)

            with action_col:
                st.markdown("**Possible action**")
                st.write(item["action"])

            with deadline_col:
                st.markdown("**Possible deadline**")
                st.write(item["deadline"])

            with st.expander("View email content"):
                st.caption(
                    f"Sender address: {item['sender_address'] or 'Unavailable'}"
                )
                st.caption(f"Date: {item['date']}")
                st.write(item["body"] or item["snippet"] or "No body text available.")

    st.divider()
    st.caption(
        "Important: priority, action, deadline, and digest preview are "
        "heuristic estimates. Review the original message before acting."
    )


# =========================================================
# FOOTER
# =========================================================
st.divider()
st.caption(
    "MailMind | ADDA Project | Gmail read-only | "
    "Local rule-based prototype"
)
