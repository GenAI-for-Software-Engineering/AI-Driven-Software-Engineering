import os
import time
import threading
from dotenv import load_dotenv

# TODO: Import libraries needed for file upload / audio-video handling
# e.g., moviepy for extracting audio from video, speech_recognition for STT

import speech_recognition as sr

import tkinter as tk
from tkinter import messagebox, filedialog

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate


load_dotenv()

key = os.getenv("GROQ_API_KEY")
if not key:
    raise RuntimeError("Missing GROQ_API_KEY")


# ---------------------------------------------------------
# Global state
# ---------------------------------------------------------
uploaded_file_path = None


# ---------------------------------------------------------
# File upload handling
# ---------------------------------------------------------
def upload_file():
    """
    TODO:
    - Open a file dialog restricted to .mp3, .wav, .mp4
    - Store the selected path in `uploaded_file_path`
    - If the file is a video (.mp4), extract audio from it
      (e.g., using moviepy) and save it as a .wav file
    - Update the UI / print a confirmation message
    """
    global uploaded_file_path
    path = filedialog.askopenfilename(
        filetypes=[("Audio/Video files", "*.mp3 *.wav *.mp4")]
    )
    if not path:
        return
    uploaded_file_path = path
    print(f"--- File selected: {uploaded_file_path} ---")

    # TODO: if path ends with .mp4, extract audio track to a .wav file
    # TODO: if path ends with .mp3, convert to .wav (speech_recognition needs wav)

    threading.Thread(target=pipe, daemon=True).start()


# ---------------------------------------------------------
# Speech-to-text
# ---------------------------------------------------------
def trans(f="input.wav"):
    """
    Convert the given audio file to text.
    TODO: Handle longer recordings (chunking) if needed.
    """
    print("\n--- Transcribing using speech_recognition ---")
    r = sr.Recognizer()
    with sr.AudioFile(f) as src:
        ad = r.record(src)
    try:
        txt = r.recognize_google(ad)
        print("--- Transcription completed ---")
        return txt
    except sr.UnknownValueError:
        return "Could not understand audio"
    except sr.RequestError as e:
        raise RuntimeError(f"Speech recognition error: {e}")


# ---------------------------------------------------------
# LLM setup
# ---------------------------------------------------------
llm = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0.2
)

# TODO: Design a prompt that extracts ONLY Functional Requirements (FR)
# from the transcript, returned as clean bullet points.
p_fr = ChatPromptTemplate.from_template("""
# TODO: Write a prompt instructing the LLM to act as a requirements
# engineer and extract Functional Requirements from {text}.
""")

# TODO: Design a prompt that extracts Non-Functional Requirements (NFR)
# from the transcript, returned as clean bullet points.
p_nfr = ChatPromptTemplate.from_template("""
# TODO: Write a prompt instructing the LLM to extract Non-Functional
# Requirements from {text}.
""")

# TODO: Design a prompt that categorizes the extracted NFRs into
# categories such as Security, Performance, Reliability, Usability, etc.
p_nfr_categorize = ChatPromptTemplate.from_template("""
# TODO: Write a prompt that takes {nfrs} and groups them under
# appropriate NFR categories.
""")


def extract_fr(t):
    """TODO: Invoke p_fr with the transcript and return the result content."""
    pass


def extract_nfr(t):
    """TODO: Invoke p_nfr with the transcript and return the result content."""
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
    Save the file and notify the user (e.g., messagebox.showinfo).
    """
    pass


# ---------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------
def pipe():
    try:
        # TODO: Use the correct wav file derived from uploaded_file_path
        t = trans("input.wav")
        print("\n========== TRANSCRIPT ==========")
        print(t)

        print("\n--- Extracting Functional Requirements ---")
        fr = extract_fr(t)
        print("\n====== FUNCTIONAL REQUIREMENTS ======")
        print(fr)

        print("\n--- Extracting Non-Functional Requirements ---")
        nfr = extract_nfr(t)
        print("\n====== NON-FUNCTIONAL REQUIREMENTS ======")
        print(nfr)

        print("\n--- Categorizing NFRs ---")
        categorized_nfr = categorize_nfr(nfr)
        print("\n====== CATEGORIZED NFRs ======")
        print(categorized_nfr)

        # TODO: Display fr / categorized_nfr in the UI in a structured format
        # (e.g., in a scrollable Text widget instead of just printing)

        # TODO: Call export_requirements() based on user's chosen format

        print("\n--- Pipeline completed successfully ---\n")

    except Exception as x:
        print("\nERROR:", x)
        messagebox.showerror("Error", str(x))


# ---------------------------------------------------------
# UI
# ---------------------------------------------------------
rt = tk.Tk()
rt.title("AI-Based Requirement Extraction")
rt.geometry("350x200")

b1 = tk.Button(rt, text="Upload Audio/Video", font=("Arial", 12), width=20, command=upload_file)
# TODO: Add buttons/widgets for:
#  - Displaying extracted FR/NFR in a structured, readable format
#  - Choosing export format (PDF/DOCX/TXT) and triggering export

b1.pack(pady=10)

rt.mainloop()
