import os
import io
import re
import json
import traceback

import speech_recognition as sr
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()

app = FastAPI()

# ==========================
# CORS
# Chrome extension pages (side panel) call this server directly.
# Allow all origins so it works regardless of the extension's
# generated ID, and regardless of whether you test it from a
# plain browser tab too.
# ==========================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    # Fail loudly at startup instead of failing mysteriously on first request.
    raise RuntimeError(
        "GROQ_API_KEY is not set. Create a .env file next to server.py "
        "with a line like: GROQ_API_KEY=your_key_here"
    )

# NOTE: llama-3.1-8b-instant was deprecated by Groq on 2026-06-17.
# openai/gpt-oss-20b is the recommended replacement.
llm = ChatGroq(
    model="openai/gpt-oss-20b",
    temperature=0.2,
    api_key=api_key
)

# ==========================
# PROMPTS
# ==========================

req_prompt = ChatPromptTemplate.from_template("""

You are a senior software requirements engineer.

Your task is to extract Functional Requirements (FR) and
Non-Functional Requirements (NFR) from a system specification.

Follow this reasoning process internally:

Step 1: Identify system actions and services.
Step 2: Identify system quality constraints.
Step 3: Classify them as FR or NFR.

Example:

Specification:
An online bookstore allows users to search books and buy them.
The system must protect user data and respond quickly.

Output:

Functional Requirements
FR1: The system shall allow users to search books.
FR2: The system shall allow users to purchase books.

Non-Functional Requirements
NFR1: The system shall ensure protection of user data.
NFR2: The system shall ensure fast response time.

Now analyze the following specification.

Return output strictly in this format:

Functional Requirements
FR1:
FR2:
FR3:

Non-Functional Requirements
NFR1:
NFR2:
NFR3:

Specification:
{text}

""")


story_prompt = ChatPromptTemplate.from_template("""

You are a senior Agile Product Owner.

Convert system requirements into Agile user stories.

User stories must follow this format.

Example:

Requirement:
The system should allow users to book flights.

User Story:

User Story 1

Front of Card
As a traveler
I want to search available flights
So that I can choose a suitable journey.

Back of Card
Acceptance Criteria
Given the traveler enters source and destination
When the search button is clicked
Then the system displays available flights.

Now generate user stories for the following requirements.

Requirements:
{requirements}

Return only user stories.

""")


invest_prompt = ChatPromptTemplate.from_template("""

You are an Agile requirements quality reviewer.

Evaluate the following user stories using the INVEST framework.

INVEST means:

Independent
Negotiable
Valuable
Estimable
Small
Testable

For each story:

Step 1: Analyze the story.
Step 2: Evaluate each INVEST criterion.
Step 3: Provide short justification.

User Stories:
{stories}

Return format:

User Story 1

Independent:
Negotiable:
Valuable:
Estimable:
Small:
Testable:

Comment:

User Story 2
...

""")


# NOTE: We deliberately do NOT ask the model to return JSON here.
# LLMs are unreliable at escaping quotes/newlines inside JSON string
# values when the value itself is a block of HTML/JS/CSS, which is
# what was causing "Prototype generation failed" before. Instead we
# ask for plain delimited sections and parse them ourselves, then
# build valid JSON on the server where we control the escaping.
prototype_prompt = ChatPromptTemplate.from_template("""

You are a UI prototype developer building a CLICKABLE, FUNCTIONAL
prototype - not a static mockup. Someone will actually click buttons,
fill in forms, and see the UI respond with real (mock) data. Bare
buttons that do nothing are a FAILED prototype.

Constraints:

1. Styling: Tailwind CSS utility classes ONLY (e.g. class="p-4
   rounded-lg shadow bg-white"). Tailwind is already loaded on the
   page - do NOT write a <style> block and do NOT write raw CSS.
2. No frameworks (no React/Vue/jQuery), just vanilla JavaScript.
3. No real backend/database. All data lives in a JavaScript object
   or array called mockData, which is already declared for you in
   the page - do NOT redeclare it, just use and mutate it.
4. The HTML section must be ONLY the inner body markup (no <html>,
   <head>, or <body> tags).
5. Build at least 3 distinct interactive elements drawn from the
   user stories (for example: a form that adds an item to a list, a
   list/table that renders from mockData, a search or filter input
   that narrows the list, a button that changes an item's status).
   Every button/form in the HTML must have a matching event handler
   in the JS that actually changes what's on screen.
6. Use a small "render" pattern: a renderX() function that rebuilds
   the relevant DOM section from the current state of mockData,
   called once on load and again after every state-changing action
   (add/edit/delete/filter). Use element IDs to target containers.
7. Do not include markdown code fences or explanations anywhere in
   your answer - only the sections below.

Here is the SHAPE of the pattern to follow (adapt the domain,
fields, and number of elements to the actual requirements/stories -
do not copy this content verbatim):

===HTML===
<div class="max-w-2xl mx-auto p-6 space-y-6">
  <h1 class="text-2xl font-bold">Example Entity Manager</h1>
  <form id="addForm" class="flex gap-2">
    <input id="nameInput" class="border rounded px-3 py-2 flex-1" placeholder="Name">
    <button type="submit" class="bg-blue-600 text-white px-4 py-2 rounded">Add</button>
  </form>
  <input id="filterInput" class="border rounded px-3 py-2 w-full" placeholder="Filter...">
  <ul id="itemList" class="divide-y divide-gray-200"></ul>
</div>
===JS===
function renderList(items) {{
  const list = document.getElementById("itemList");
  list.innerHTML = items.map((item, i) =>
    `<li class="flex justify-between items-center py-2">
       <span>${{item.name}}</span>
       <button data-index="${{i}}" class="deleteBtn text-red-600">Delete</button>
     </li>`
  ).join("");
  document.querySelectorAll(".deleteBtn").forEach(btn => {{
    btn.addEventListener("click", () => {{
      mockData.items.splice(Number(btn.dataset.index), 1);
      renderList(mockData.items);
    }});
  }});
}}
document.getElementById("addForm").addEventListener("submit", (e) => {{
  e.preventDefault();
  const input = document.getElementById("nameInput");
  if (input.value.trim()) {{
    mockData.items.push({{ name: input.value.trim() }});
    input.value = "";
    renderList(mockData.items);
  }}
}});
document.getElementById("filterInput").addEventListener("input", (e) => {{
  const q = e.target.value.toLowerCase();
  renderList(mockData.items.filter(i => i.name.toLowerCase().includes(q)));
}});
renderList(mockData.items);
===DATA===
{{"items":[{{"name":"Sample item"}}]}}
===END===

Now generate a prototype following that pattern, sized to the
requirements and user stories below.

Requirements:
{requirements}

User Stories:
{stories}

Return your answer using EXACTLY this structure, with each marker
on its own line and nothing else on that line:

===HTML===
(html markup here)
===JS===
(javascript here)
===DATA===
(a single JSON object with mock data here)
===END===

""")


test_prompt = ChatPromptTemplate.from_template("""

You are a professional software test engineer.

Generate test cases for the system using the user stories below.
These test cases will be executed manually by a human tester
against a live prototype, so each step must be something a person
can physically do by clicking/typing in a UI (not internal/backend
checks).

Reason step-by-step internally:

1. Identify system functionality from the user stories.
2. Determine possible user interactions (happy path AND at least
   one edge case per story where relevant, e.g. empty input).
3. Create test cases to verify system behaviour.

Return ONLY a JSON array, nothing else - no markdown fences, no
explanation before or after it. Each element must have exactly
these keys:

- "id": short id like "TC1"
- "title": short description
- "steps": array of strings, each one concrete UI action
- "expected": a single string describing the expected result

Example output:

[
  {{
    "id": "TC1",
    "title": "Search returns matching flights",
    "steps": ["Enter a valid source airport", "Enter a valid destination airport", "Click the search button"],
    "expected": "A list of available flights for that route is displayed"
  }}
]

User Stories:
{stories}

""")

# ==========================
# MODELS
# ==========================

class TextSpec(BaseModel):
    text: str

class ReqModel(BaseModel):
    requirements: str

class StoryModel(BaseModel):
    stories: str

class PrototypeModel(BaseModel):
    requirements: str
    stories: str


# ==========================
# AUDIO TRANSCRIBE
# ==========================

def transcribe_audio(audio_bytes: bytes) -> str:

    r = sr.Recognizer()

    with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
        audio = r.record(source)

    return r.recognize_google(audio)


# ==========================
# PROTOTYPE PARSING HELPER
# ==========================

def parse_prototype_response(raw_text: str):
    """
    Parses the ===HTML===/===JS===/===DATA===/===END=== delimited
    response format into a dict. Tolerant of minor formatting
    variance from the LLM (extra whitespace, missing END marker,
    stray markdown fences).
    """

    cleaned = raw_text.strip()
    cleaned = re.sub(r"```[a-zA-Z]*", "", cleaned)
    cleaned = cleaned.replace("```", "")

    def extract(section_name, text, next_markers):
        pattern = r"===" + section_name + r"===\s*(.*?)"
        pattern += r"(?=" + "|".join(r"===" + m + r"===" for m in next_markers) + r"|$)"
        match = re.search(pattern, text, re.DOTALL)
        return match.group(1).strip() if match else ""

    html_part = extract("HTML", cleaned, ["JS", "DATA", "END"])
    js_part = extract("JS", cleaned, ["DATA", "END"])
    data_part = extract("DATA", cleaned, ["END"])

    if not html_part:
        raise ValueError("Model response did not contain an ===HTML=== section")

    # Validate/normalize the mock data into real JSON text.
    data_part = data_part.strip()
    if not data_part:
        data_part = "{}"
    else:
        try:
            parsed = json.loads(data_part)
            data_part = json.dumps(parsed)
        except json.JSONDecodeError:
            # Model returned non-JSON mock data - fall back to empty
            # object rather than breaking the whole prototype.
            data_part = "{}"

    return {
        "html": html_part,
        "js": js_part,
        "data": data_part
    }


def parse_test_cases_response(raw_text: str):
    """
    Parses the model's test-case JSON array, tolerant of stray
    markdown fences or leading/trailing prose. Falls back to a
    single free-text test case (so nothing is silently lost) if
    the model didn't return valid JSON.
    """

    cleaned = raw_text.strip()
    cleaned = re.sub(r"```[a-zA-Z]*", "", cleaned).replace("```", "").strip()

    # If there's stray prose around the array, grab just the [...] part.
    match = re.search(r"\[.*\]", cleaned, re.DOTALL)
    if match:
        cleaned = match.group(0)

    try:
        parsed = json.loads(cleaned)
        if not isinstance(parsed, list):
            raise ValueError("not a list")

        normalized = []
        for i, item in enumerate(parsed):
            normalized.append({
                "id": str(item.get("id", f"TC{i + 1}")),
                "title": str(item.get("title", "Untitled test case")),
                "steps": [str(s) for s in item.get("steps", [])],
                "expected": str(item.get("expected", ""))
            })
        return normalized

    except (json.JSONDecodeError, ValueError, AttributeError):
        # Fall back so the raw content is still usable, rather than
        # erroring out the whole stage.
        return [{
            "id": "TC1",
            "title": "Generated test cases (unstructured)",
            "steps": [raw_text.strip()],
            "expected": ""
        }]


# ==========================
# STAGE 1
# ==========================

@app.post("/extract_text")
def extract_text(req: TextSpec):

    try:
        chain = req_prompt | llm
        result = chain.invoke({"text": req.text})
        return {"requirements": result.content}

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/extract_audio")
async def extract_audio(file: UploadFile = File(...)):

    try:
        audio_bytes = await file.read()

        try:
            transcript = transcribe_audio(audio_bytes)
        except sr.UnknownValueError:
            raise HTTPException(status_code=422, detail="Could not understand the audio")
        except sr.RequestError as e:
            raise HTTPException(status_code=502, detail=f"Speech recognition service error: {e}")

        if not transcript:
            raise HTTPException(status_code=422, detail="No speech detected in audio")

        chain = req_prompt | llm
        result = chain.invoke({"text": transcript})

        return {"requirements": result.content, "transcript": transcript}

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ==========================
# STAGE 2A
# ==========================

@app.post("/generate_user_stories")
def generate_stories(req: ReqModel):

    try:
        chain = story_prompt | llm
        result = chain.invoke({"requirements": req.requirements})
        return {"stories": result.content}

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ==========================
# STAGE 2B
# ==========================

@app.post("/verify_invest")
def verify(req: StoryModel):

    try:
        chain = invest_prompt | llm
        result = chain.invoke({"stories": req.stories})
        return {"invest": result.content}

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ==========================
# STAGE 3
# ==========================

@app.post("/generate_prototype")
def generate_proto(req: PrototypeModel):

    try:
        chain = prototype_prompt | llm

        result = chain.invoke({
            "requirements": req.requirements,
            "stories": req.stories
        })

        parsed = parse_prototype_response(result.content)

        return parsed

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ==========================
# STAGE 4
# ==========================

@app.post("/generate_tests")
def generate_tests(req: StoryModel):

    try:
        chain = test_prompt | llm
        result = chain.invoke({"stories": req.stories})
        test_cases = parse_test_cases_response(result.content)
        return {"tests": test_cases}

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ==========================
# HEALTH CHECK
# ==========================

@app.get("/health")
def health():
    return {"status": "ok"}
