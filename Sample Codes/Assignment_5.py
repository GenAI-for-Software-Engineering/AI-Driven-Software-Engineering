import os
import io
import zlib
import requests
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

Using the transcript below generate:

Functional Requirements
Non Functional Requirements

Use bullet points.

Transcript:
{text}
""")


p_gap = ChatPromptTemplate.from_template("""
You are a senior requirements engineer.

Using the transcript and current requirements generate EXACTLY 10 clarification questions.

Transcript:
{transcript}

Current Requirements:
{requirements}

Return numbered list.
""")


p_improve = ChatPromptTemplate.from_template("""
You are a senior requirements engineer.

Using:

Transcript
Current Requirements
Clarification Questions
Stakeholder Answers

Generate improved:

Functional Requirements
Non Functional Requirements

Transcript:
{transcript}

Current Requirements:
{requirements}

Questions:
{questions}

Answers:
{answers}
""")


# =====================================
# USER STORIES PROMPT
# =====================================

# TODO: Write a prompt that takes the verified requirements and
# generates Agile User Stories. Each story should include:
# - A User Story ID
# - Front of card: "As a <role> I want <feature> so that <benefit>"
# - Back of card: Acceptance Criteria using Given/When/Then
p_userstories = ChatPromptTemplate.from_template("""
# TODO: Instruct the LLM (acting as a senior Agile Product Owner) to
# derive actors, actions, and workflows from {requirements} and
# produce structured user stories as described above.
""")


# =====================================
# ACTIVITY DIAGRAM PROMPT
# =====================================

# TODO: Write a prompt that takes the generated user stories and
# produces a UML Activity Diagram in PlantUML syntax. Remember the
# strict rules the assignment needs:
# - Must be an Activity Diagram (start/stop/:action;/if-then-else/fork)
# - Must NOT use sequence diagram syntax (participant, actor, ->, etc.)
# - Output must start with @startuml and end with @enduml
p_activity = ChatPromptTemplate.from_template("""
# TODO: Instruct the LLM (acting as a UML expert) to convert
# {stories} into valid PlantUML Activity Diagram code, following the
# strict syntax rules above. Return ONLY the PlantUML code.
""")


# =====================================
# FUNCTIONS
# =====================================

def generate_requirements(text):
    return (p_req | llm).invoke({"text": text}).content


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


def generate_user_stories(requirements):
    """TODO: Invoke p_userstories with the requirements and return the result content."""
    pass


def generate_activity_code(stories):
    """TODO: Invoke p_activity with the user stories and return the result content."""
    pass


# =====================================
# CLEAN UML OUTPUT
# =====================================

def clean_plantuml_output(text):
    """
    Extract only the text between @startuml and @enduml (inclusive),
    in case the LLM adds extra commentary around the diagram code.
    """
    start = text.find("@startuml")
    end = text.find("@enduml")

    if start != -1 and end != -1:
        return text[start:end+7]

    return text


# =====================================
# PLANTUML ENCODING
# =====================================

def plantuml_encode(text):
    """
    Encode PlantUML source into the compressed text format required
    by the public PlantUML rendering server.

    TODO: You can keep this helper as-is (it's boilerplate encoding
    logic), but make sure you understand roughly what it does:
    1. zlib-compress the PlantUML text
    2. Re-encode the compressed bytes using PlantUML's custom
       base64-like alphabet, 3 bytes -> 4 chars at a time
    """
    zlibbed = zlib.compress(text.encode("utf-8"))
    compressed = zlibbed[2:-4]

    alphabet = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_"

    def encode6bit(b):
        if b < 10:
            return chr(48 + b)
        b -= 10
        if b < 26:
            return chr(65 + b)
        b -= 26
        if b < 26:
            return chr(97 + b)
        b -= 26
        if b == 0:
            return "-"
        if b == 1:
            return "_"

    def append3bytes(b1, b2, b3):
        c1 = b1 >> 2
        c2 = ((b1 & 0x3) << 4) | (b2 >> 4)
        c3 = ((b2 & 0xF) << 2) | (b3 >> 6)
        c4 = b3 & 0x3F
        return "".join(map(encode6bit, [c1, c2, c3, c4]))

    res = ""
    i = 0

    while i < len(compressed):
        b1 = compressed[i]
        b2 = compressed[i+1] if i+1 < len(compressed) else 0
        b3 = compressed[i+2] if i+2 < len(compressed) else 0
        res += append3bytes(b1, b2, b3)
        i += 3

    return res


def generate_activity_image(plantuml_code):
    """
    TODO: Use plantuml_encode() to build the request URL and fetch
    the rendered diagram image from the PlantUML server, then save
    it locally (e.g. as "activity_diagram.png") and return the path.
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

if "userstories" not in st.session_state:
    st.session_state.userstories = None

if "activity_image" not in st.session_state:
    st.session_state.activity_image = None


# =====================================
# UI
# =====================================

st.title("Voice Driven Requirements Engineering")

mode = st.radio("Choose Input Method:", ["Record Audio", "Upload Audio File"])

audio_bytes = None

if mode == "Record Audio":
    audio = st.audio_input("Record requirements")
    if audio:
        audio_bytes = audio.read()

else:
    uploaded = st.file_uploader("Upload WAV", type=["wav"])
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


# =====================================
# ITERATIVE LOOP
# =====================================

if st.session_state.requirements and not st.session_state.verified:

    st.subheader(f"Requirements Iteration {st.session_state.iteration}")
    st.markdown(st.session_state.requirements)

    if st.button("Analyze Gap"):

        st.session_state.gap_questions = generate_gap_questions(
            st.session_state.requirements,
            st.session_state.transcript
        )

    if st.session_state.gap_questions:

        raw_lines = st.session_state.gap_questions.split("\n")

        questions = []

        for line in raw_lines:
            line = line.strip()
            if line and line[0].isdigit():
                questions.append(line)

        questions = questions[:10]

        answers = []

        for i, q in enumerate(questions):

            st.markdown(q)

            ans = st.text_input(
                f"Answer {i+1}",
                key=f"a_{st.session_state.iteration}_{i}"
            )

            answers.append(ans)

        if st.button("Submit Answers"):

            compiled = ""

            for i, q in enumerate(questions):
                compiled += f"{q}\nAnswer: {answers[i]}\n\n"

            improved = improve_requirements(
                st.session_state.requirements,
                st.session_state.transcript,
                st.session_state.gap_questions,
                compiled
            )

            st.session_state.requirements = improved
            st.session_state.gap_questions = None
            st.session_state.iteration += 1

            st.success("Requirements improved")
            st.rerun()

    if st.button("Verified"):
        st.session_state.verified = True
        st.success("Requirements finalized")


# =====================================
# FINAL OUTPUT
# =====================================

if st.session_state.verified:

    st.subheader("Final Requirements")
    st.markdown(st.session_state.requirements)

    st.subheader("User Stories")

    if st.session_state.userstories is None:

        if st.button("Generate User Stories"):

            # TODO: generate_user_stories() currently returns None
            # (see the TODO above) — implement it before this will work.
            stories = generate_user_stories(st.session_state.requirements)

            st.session_state.userstories = stories

            st.rerun()

    if st.session_state.userstories:

        st.markdown(st.session_state.userstories)

        # TODO: Allow the user to edit/refine the generated user
        # stories here (e.g. st.text_area bound back into
        # st.session_state.userstories) before moving on to the
        # activity diagram, per the "Allow editing or refinement of
        # generated User Stories" feature.

        st.subheader("Activity Diagram")

        if st.session_state.activity_image is None:

            if st.button("Generate Activity Diagram"):

                # TODO: generate_activity_code() currently returns None
                # and generate_activity_image() is unimplemented —
                # fill both in before this section will work.
                code = generate_activity_code(st.session_state.userstories)

                code = clean_plantuml_output(code)

                img = generate_activity_image(code)

                st.session_state.activity_image = img

                st.rerun()

        if st.session_state.activity_image:

            st.image(st.session_state.activity_image)

        # TODO: Add export controls (PDF/DOCX/TXT) for the final
        # requirements, user stories, and activity diagram, per the
        # "Export generated artifacts as PDF/DOCX/TXT" feature.
