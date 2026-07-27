import os
import base64
from dotenv import load_dotenv

import streamlit as st

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate


load_dotenv()
GROQ_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_KEY:
    st.error("Missing GROQ_API_KEY")
    st.stop()

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


# ---------------------------------------------------------
# Gmail Authentication
# ---------------------------------------------------------
def gmail_auth():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(
            "credentials.json", SCOPES
        )
        creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    service = build("gmail", "v1", credentials=creds)
    return service


# ---------------------------------------------------------
# Fetch Emails
# ---------------------------------------------------------
def get_emails(service, keyword):
    """
    Fetch emails matching a keyword/subject.
    TODO: Consider also searching body content, not just subject,
    depending on how you want to "filter relevant project-related emails".
    """
    results = service.users().messages().list(
        userId="me",
        q=f'subject:{keyword}',
        maxResults=10
    ).execute()

    msgs = list(reversed(results.get("messages", [])))
    texts = []

    for m in msgs:
        msg = service.users().messages().get(
            userId="me",
            id=m["id"],
            format="full"
        ).execute()

        payload = msg["payload"]
        headers = payload.get("headers", [])

        subject = ""
        for h in headers:
            if h["name"] == "Subject":
                subject = h["value"]

        body = ""

        if "data" in payload.get("body", {}):
            body = payload["body"]["data"]
        else:
            parts = payload.get("parts", [])
            for p in parts:
                if p["mimeType"] == "text/plain":
                    body = p["body"].get("data", "")
                    break

        if body:
            body = base64.urlsafe_b64decode(body).decode("utf-8")

        text = f"Subject: {subject}\nBody: {body}"
        texts.append(text)

    return "\n\n".join(texts)


# ---------------------------------------------------------
# TODO: Filtering / Preprocessing
# ---------------------------------------------------------
def filter_relevant_emails(raw_text):
    """
    TODO: Given the combined raw email text, filter out irrelevant
    emails (e.g., newsletters, spam, non-project emails) and clean
    up formatting (signatures, quoted reply chains, HTML leftovers).
    Return the cleaned, relevant text.
    """
    pass


# ---------------------------------------------------------
# LLM setup
# ---------------------------------------------------------
llm = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0.2
)

# TODO: Write a prompt that reads the (cleaned) email text and flags
# any vague or incomplete requirement statements before extraction.
p_vague = ChatPromptTemplate.from_template("""
# TODO: Instruct the LLM to identify vague/incomplete requirement
# statements in {text} and note what clarification is needed.
""")

# TODO: Write a prompt that extracts ONLY Functional Requirements (FR)
p_fr = ChatPromptTemplate.from_template("""
# TODO: Extract Functional Requirements from {text}.
""")

# TODO: Write a prompt that extracts ONLY Non-Functional Requirements (NFR)
p_nfr = ChatPromptTemplate.from_template("""
# TODO: Extract Non-Functional Requirements from {text}.
""")

# TODO: Write a prompt that categorizes NFRs into categories such as
# Security, Performance, Reliability, Usability, etc.
p_nfr_categorize = ChatPromptTemplate.from_template("""
# TODO: Group {nfrs} under appropriate NFR categories.
""")


def detect_vague(t):
    """TODO: Invoke p_vague with the email text and return the result content."""
    pass


def extract_fr(t):
    """TODO: Invoke p_fr with the email text and return the result content."""
    pass


def extract_nfr(t):
    """TODO: Invoke p_nfr with the email text and return the result content."""
    pass


def categorize_nfr(n):
    """TODO: Invoke p_nfr_categorize with extracted NFRs and return result."""
    pass


# ---------------------------------------------------------
# Export functionality
# ---------------------------------------------------------
def export_requirements(fr, nfr, fmt="txt"):
    """
    TODO: Implement export of generated requirements.
    - fmt == "txt": simple text file write
    - fmt == "pdf": use a PDF library (e.g., reportlab / fpdf)
    - fmt == "docx": use python-docx
    Save the file and provide a download link/button via st.download_button.
    """
    pass


# ---------------------------------------------------------
# UI
# ---------------------------------------------------------
st.title("Email Driven Requirements Engineering")

kw = st.text_input("Enter Keyword")

if st.button("Fetch Emails"):
    with st.spinner("Authenticating with Gmail..."):
        svc = gmail_auth()

    with st.spinner("Fetching Emails..."):
        raw_text = get_emails(svc, kw)

    if not raw_text:
        st.error("No matching emails found")
        st.stop()

    st.subheader("Email Content")
    st.markdown(raw_text)

    # TODO: Call filter_relevant_emails() here before analysis
    text = raw_text  # placeholder — replace with cleaned/filtered text

    st.subheader("Vague / Incomplete Requirements")
    vague = detect_vague(text)
    st.markdown(vague)

    st.subheader("Functional Requirements")
    fr = extract_fr(text)
    st.markdown(fr)

    st.subheader("Non-Functional Requirements")
    nfr = extract_nfr(text)
    st.markdown(nfr)

    st.subheader("Categorized NFRs")
    categorized_nfr = categorize_nfr(nfr)
    st.markdown(categorized_nfr)

    # TODO: Add UI controls (e.g., st.selectbox / buttons) to choose
    # export format (PDF/DOCX/TXT) and call export_requirements()
