import os
import streamlit as st
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate


load_dotenv()

api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    st.error("Missing GROQ_API_KEY in .env file")
    st.stop()

llm = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0.0
)


def run_step(prompt_text, code):
    """
    Generic helper: runs a single refactoring step by sending the
    given system prompt + current Java code to the LLM and returning
    the updated code as a string.
    """
    prompt = ChatPromptTemplate.from_messages([
        ("system", prompt_text),
        ("human", "Java Code:\n{input}")
    ])
    chain = prompt | llm
    response = chain.invoke({"input": code})
    return response.content


# =====================================
# REFACTORING PROMPTS
# =====================================
# TODO (Q11): Write a system prompt that refactors the Java code to
# follow the Single Responsibility Principle — split large classes
# (e.g. the Bank class) into smaller ones, each with one responsibility.
# The prompt should instruct the LLM to return the full updated code only.
SRP_PROMPT = """
# TODO: instruct the LLM to identify multiple responsibilities in the
# uploaded Java class(es) and split them into separate, single-purpose
# classes, while preserving functionality.
"""

# TODO (Q12): Write a system prompt that removes instanceof / if-else
# type-checking logic and replaces it with polymorphism, to follow the
# Open/Closed Principle.
OCP_PROMPT = """
# TODO: instruct the LLM to remove instanceof/if-else type checks
# (e.g. in methods like withdraw()) and redesign the class hierarchy
# to use polymorphism instead.
"""

# TODO (Q13): Write a system prompt that redesigns object creation
# logic using the Factory design pattern.
FACTORY_PROMPT = """
# TODO: instruct the LLM to apply the Factory Pattern for object
# creation (e.g. account creation) and remove direct instantiation
# logic from calling code.
"""

# TODO (Q14): Write a system prompt that splits a large interface
# (e.g. BankingOperations) into smaller, role-specific interfaces to
# follow the Interface Segregation Principle.
ISP_PROMPT = """
# TODO: instruct the LLM to split the interface into smaller
# interfaces so that implementers (e.g. ATM, MobileApp) are not
# forced to depend on methods they do not use.
"""

# TODO (Q15): Write a system prompt that applies Dependency Inversion
# / Dependency Injection (e.g. in LoanService) to remove tight
# coupling between classes.
DIP_PROMPT = """
# TODO: instruct the LLM to apply the Dependency Inversion Principle
# — depend on abstractions, inject dependencies (e.g. via
# constructor), and remove tight coupling.
"""

# TODO: Write a final cleanup prompt that reviews the fully
# refactored code, ensures all SOLID principles are consistently
# applied, improves readability, and removes redundancy.
FINAL_CLEANUP_PROMPT = """
# TODO: instruct the LLM to do a final pass over the code: verify
# SOLID compliance, improve structure/formatting, remove
# redundancies, and return production-quality code.
"""


st.set_page_config(page_title="AI Refactoring Engine", layout="wide")

st.title("AI Refactoring Engine (SOLID + Design Patterns)")
st.markdown("Upload Java code → Get fully refactored clean architecture")

uploaded_file = st.file_uploader("Upload Java File", type=["java", "txt"])


if uploaded_file is not None:

    code = uploaded_file.read().decode("utf-8")

    st.subheader("Original Code")
    st.code(code, language="java")

    if st.button("Refactor Code"):

        with st.spinner("Running multi-step AI refactoring... 🧠⚙️"):

            # TODO: Each step below feeds the previous step's output
            # into the next prompt. Once you've written the prompts
            # above (Q11-Q15), this pipeline should run end-to-end.
            step1 = run_step(SRP_PROMPT, code)
            step2 = run_step(OCP_PROMPT, step1)
            step3 = run_step(FACTORY_PROMPT, step2)
            step4 = run_step(ISP_PROMPT, step3)
            step5 = run_step(DIP_PROMPT, step4)

            final_code = run_step(FINAL_CLEANUP_PROMPT, step5)

        st.subheader("Fully Refactored Code")
        st.code(final_code, language="java")

        # TODO (Section 3/5): Consider logging or displaying how many
        # iterations/prompts were needed and what changed at each step,
        # to help answer Q21-Q23 (advanced LLM thinking questions).

        with st.expander("Intermediate Steps (For Analysis)"):
            st.write("### SRP Output")
            st.code(step1, language="java")

            st.write("### Polymorphism Output")
            st.code(step2, language="java")

            st.write("### Factory Output")
            st.code(step3, language="java")

            st.write("### ISP Output")
            st.code(step4, language="java")

            st.write("### DIP Output")
            st.code(step5, language="java")

        # TODO (Section 4): Add a way to compare this LLM-generated
        # refactoring against your manual refactoring from Section 2
        # (e.g. side-by-side st.code blocks or a diff view) to support
        # your answers to Q16-Q20.
