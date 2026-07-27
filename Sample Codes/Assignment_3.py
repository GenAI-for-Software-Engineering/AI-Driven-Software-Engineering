import os
import io
from dotenv import load_dotenv

import speech_recognition as sr
import streamlit as st

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate


# =====================================
# LOAD ENV
# =====================================

load_dotenv()

key = os.getenv("GROQ_API_KEY")
if not key:
    st.error("Missing GROQ_API_KEY")
    st.stop()


# =====================================
# SPEECH TO TEXT
# =====================================

def transcribe_audio(audio_bytes):
    r = sr.Recognizer()
    with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
        audio = r.record(source)

    try:
        return r.recognize_google(audio)
    except sr.UnknownValueError:
        return "Could not understand audio"
    except sr.RequestError as e:
        return f"Speech recognition error: {e}"


# TODO: Add an email-fetching path (Gmail API) as an alternative input
# source, similar to transcribe_audio() but returning raw email text
# instead of a transcript. The rest of the pipeline (extraction,
# gap analysis, refinement) should work the same on either input.
def fetch_emails(keyword):
    """
    TODO: Authenticate with Gmail, fetch messages matching `keyword`,
    and return the combined text (subject + body) to feed into the
    requirements pipeline.
    """
    pass


# =====================================
# LLM
# =====================================

llm = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0.2
)


# =====================================
# PROMPTS
# =====================================

p_req = ChatPromptTemplate.from_template("""
You are a senior software requirements engineer.

Using the transcript below, generate:

- Functional Requirements
- Non-Functional Requirements

Use bullet points.

Transcript:
{text}
""")

# TODO: Write a prompt that looks at the current requirements and flags
# which ones are vague, ambiguous, or incomplete (before generating
# clarification questions). This should feed into / inform p_gap below.
p_vague = ChatPromptTemplate.from_template("""
# TODO: Instruct the LLM to identify vague/ambiguous/incomplete
# requirement statements in {requirements} and briefly explain why
# each one is unclear.
""")

p_gap = ChatPromptTemplate.from_template("""
You are a senior requirements engineer.

Using the transcript and current requirements,
generate EXACTLY 10 clarification questions.

All questions must relate strictly to this system.

Transcript:
{transcript}

Current Requirements:
{requirements}

Return numbered list (1-10).
""")

p_improve = ChatPromptTemplate.from_template("""
You are a senior requirements engineer.

Using:

- Transcript
- Current Requirements
- Clarification Questions
- Stakeholder Answers

Generate improved:

- Functional Requirements
- Non-Functional Requirements

Transcript:
{transcript}

Current Requirements:
{requirements}

Questions:
{questions}

Answers:
{answers}

Return bullet points.
""")

# TODO: Write a prompt that takes the final refined requirements and
# categorizes the NFRs into groups such as Security, Performance,
# Reliability, Usability, etc.
p_nfr_categorize = ChatPromptTemplate.from_template("""
# TODO: Group the NFRs found in {requirements} under appropriate
# categories.
""")


# =====================================
# FUNCTIONS
# =====================================

def generate_requirements(text):
    return (p_req | llm).invoke({"text": text}).content


def detect_vague_requirements(requirements):
    """TODO: Invoke p_vague with the current requirements and return the result content."""
    pass


def generate_gap_questions(requirements, transcript):
    return (p_gap | llm).invoke({
        "requirements": requirements,
        "transcript": transcript
    }).content


def improve_requirements(requirements, transcript, questions, answers):
    return (p_improve | llm).invoke({
        "requirements": requirements,
        "transcript": transcript,
        "questions": questions,
        "answers": answers
    }).content


def categorize_nfrs(requirements):
    """TODO: Invoke p_nfr_categorize with the final requirements and return the result content."""
    pass


# ---------------------------------------------------------
# Export functionality
# ---------------------------------------------------------
def export_requirements(requirements, fmt="txt"):
    """
    TODO: Implement export of the final verified requirements.
    - fmt == "txt": simple text file write
    - fmt == "pdf": use a PDF library (e.g., reportlab / fpdf)
    - fmt == "docx": use python-docx
    Provide a download link/button via st.download_button.
    """
    pass


# =====================================
# SESSION STATE
# =====================================

if "requirements" not in st.session_state:
    st.session_state.requirements = None

if "gap_questions" not in st.session_state:
    st.session_state.gap_questions = None

if "verified" not in st.session_state:
    st.session_state.verified = False

if "iteration" not in st.session_state:
    st.session_state.iteration = 0

if "transcript" not in st.session_state:
    st.session_state.transcript = None

if "answers" not in st.session_state:
    st.session_state.answers = [""] * 10


# =====================================
# UI
# =====================================

st.title("🎙️ Voice Driven Requirements Engineering")

mode = st.radio("Choose Input Method:", ["Record Audio", "Upload Audio File"])
# TODO: Add a third option, e.g. "Fetch from Email", that calls
# fetch_emails() instead of transcribe_audio() and stores the result
# in st.session_state.transcript (rename/reuse as a generic "source text").

audio_bytes = None

if mode == "Record Audio":
    audio = st.audio_input("Record your requirements")
    if audio:
        audio_bytes = audio.read()

else:
    uploaded = st.file_uploader("Upload WAV file", type=["wav"])
    if uploaded:
        audio_bytes = uploaded.read()


# =====================================
# INITIAL GENERATION
# =====================================

if audio_bytes and st.session_state.requirements is None:

    st.subheader("Transcript")
    transcript = transcribe_audio(audio_bytes)
    st.session_state.transcript = transcript
    st.markdown(transcript)

    st.subheader("Generated Requirements")
    reqs = generate_requirements(transcript)
    st.session_state.requirements = reqs
    st.markdown(reqs)

    # TODO: Show initial vague/ambiguous requirements here using
    # detect_vague_requirements(), before moving into the gap-question loop.


# =====================================
# ITERATIVE LOOP
# =====================================

if st.session_state.requirements and not st.session_state.verified:

    st.subheader(f"Current Requirements (Iteration {st.session_state.iteration})")
    st.markdown(st.session_state.requirements)

    if st.button("Analyze Gap"):
        st.session_state.gap_questions = generate_gap_questions(
            st.session_state.requirements,
            st.session_state.transcript
        )
        st.session_state.answers = [""] * 10

    if st.session_state.gap_questions:

        st.subheader("Clarification Questions")

        # Extract only non-empty lines
        raw_lines = st.session_state.gap_questions.split("\n")
        questions = []

        for line in raw_lines:
            line = line.strip()
            # Accept only numbered questions
            if line and line[0].isdigit():
                questions.append(line)


        questions = questions[:10]

        user_answers = []

        for i, question in enumerate(questions):

            st.markdown(f"**{question}**")

            answer = st.text_input(
                label=f"Answer {i+1}",
                key=f"answer_{st.session_state.iteration}_{i}"
            )

            user_answers.append(answer)

        if st.button("Submit Answers"):

            compiled_answers = ""

            for i, question in enumerate(questions):
                compiled_answers += f"{question}\n"
                compiled_answers += f"Answer: {user_answers[i]}\n\n"

            improved = improve_requirements(
                st.session_state.requirements,
                st.session_state.transcript,
                st.session_state.gap_questions,
                compiled_answers
            )

            st.session_state.requirements = improved
            st.session_state.gap_questions = None
            st.session_state.iteration += 1

            st.success("Requirements Improved Successfully!")
            st.rerun()


    if st.button("Verified"):
        st.session_state.verified = True
        st.success("Requirements Verified and Finalized!")


# =====================================
# FINAL OUTPUT
# =====================================

if st.session_state.verified:
    st.subheader("✅ Final Verified Requirements")
    st.markdown(st.session_state.requirements)

    # TODO: Call categorize_nfrs() on the final requirements and
    # display the categorized NFRs (e.g., st.subheader("Categorized NFRs")).

    # TODO: Add UI controls (e.g., st.selectbox / buttons) to choose
    # export format (PDF/DOCX/TXT) and call export_requirements().
