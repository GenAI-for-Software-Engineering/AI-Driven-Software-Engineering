import os
import zlib
import requests
import streamlit as st
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate


# =====================================
# LOAD ENV
# =====================================

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")


# =====================================
# LLM
# =====================================

llm = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0.2,
    api_key=api_key
)


# =====================================
# PROMPTS
# =====================================

p_classes = ChatPromptTemplate.from_template("""

You are a senior software architect.

Your task is to identify conceptual classes from a system specification.

Follow this reasoning internally:

Step 1: Identify domain entities.
Step 2: Ignore primitive data types.
Step 3: Select meaningful domain objects.

Example:

Specification:
An online bookstore allows customers to search books and place orders.

Classes:
Customer
Book
Order
Payment

Now analyze the following specification.

Return ONLY the class names.

Specification:
{text}

""")


p_attributes = ChatPromptTemplate.from_template("""

You are a senior software architect.

For each class identify attributes.

Reason internally:

1. Understand the purpose of the class.
2. Identify the information it stores.

Return attributes in this format:

ClassName
- attribute
- attribute

Classes:
{classes}

Specification:
{text}

""")

p_methods = ChatPromptTemplate.from_template("""

You are a senior software architect.

Identify methods for each class.

Reason internally:

1. Identify responsibilities of the class.
2. Convert actions into methods.

Return methods in this format:

ClassName
+method()
+method()

Classes:
{classes}

Specification:
{text}

""")


p_relationships = ChatPromptTemplate.from_template("""

You are a senior software architect.

Identify relationships between classes.

Reason internally:

1. Identify which classes interact.
2. Determine association or multiplicity.

Return relationships like:

ClassA --> ClassB
ClassA "1" -- "*" ClassB

Classes:
{classes}

Specification:
{text}

""")



p_uml = ChatPromptTemplate.from_template("""

You are a UML modeling expert.

Generate a PlantUML class diagram.

Constraints:

- Include classes
- Include attributes
- Include methods
- Include relationships
- Include visibility specifiers (+, -, #)

Return ONLY PlantUML code.

Example:

@startuml

class Example {{
+attribute
-method()
}}

Example --> Other

@enduml

Classes:
{classes}

Attributes:
{attributes}

Methods:
{methods}

Relationships:
{relationships}

""")


# =====================================
# LLM FUNCTIONS
# =====================================

def identify_classes(text):
    return (p_classes | llm).invoke({"text": text}).content


def identify_attributes(classes, text):
    return (p_attributes | llm).invoke({
        "classes": classes,
        "text": text
    }).content


def identify_methods(classes, text):
    return (p_methods | llm).invoke({
        "classes": classes,
        "text": text
    }).content


def identify_relationships(classes, text):
    return (p_relationships | llm).invoke({
        "classes": classes,
        "text": text
    }).content


def generate_uml(classes, attributes, methods, relationships):
    return (p_uml | llm).invoke({
        "classes": classes,
        "attributes": attributes,
        "methods": methods,
        "relationships": relationships
    }).content


# =====================================
# CLEAN UML OUTPUT
# =====================================

def clean_plantuml_output(text):

    text = text.replace("```plantuml", "")
    text = text.replace("```", "")
    text = text.strip()

    if "@startuml" not in text:
        text = "@startuml\n" + text

    if "@enduml" not in text:
        text = text + "\n@enduml"

    return text


# =====================================
# PLANTUML ENCODER
# =====================================

def plantuml_encode(text):

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


# =====================================
# RENDER DIAGRAM
# =====================================

def render_diagram(uml_code):

    encoded = plantuml_encode(uml_code)

    url = f"https://www.plantuml.com/plantuml/png/{encoded}"

    response = requests.get(url)

    with open("class_diagram.png", "wb") as f:
        f.write(response.content)

    return "class_diagram.png"


# =====================================
# STREAMLIT UI
# =====================================

st.title("LLM-based UML Class Diagram Generator")

spec = st.text_area(
    "Enter Airline Ticketing System Specification",
    height=250
)


if st.button("Generate Class Diagram"):

    st.header("Step 1 — Identified Classes")

    classes = identify_classes(spec)

    st.write(classes)


    st.header("Step 2 — Attributes")

    attributes = identify_attributes(classes, spec)

    st.write(attributes)


    st.header("Step 3 — Methods")

    methods = identify_methods(classes, spec)

    st.write(methods)


    st.header("Step 4 — Relationships")

    relationships = identify_relationships(classes, spec)

    st.write(relationships)


    st.header("Step 5 — PlantUML Code")

    uml_code = generate_uml(classes, attributes, methods, relationships)

    uml_code = clean_plantuml_output(uml_code)

    st.code(uml_code)


    st.header("Step 6 — UML Class Diagram")

    img = render_diagram(uml_code)

    st.image(img)