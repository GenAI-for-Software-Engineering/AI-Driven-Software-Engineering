import os
import json
import re
import shutil
import subprocess
import time
from dotenv import load_dotenv
from langchain_groq import ChatGroq


load_dotenv()

api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    raise ValueError("Missing GROQ_API_KEY")

llm = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0.2,
)

ORIGINAL_FILE = "source_code_original.py"
WORKING_FILE = "source_code.py"
REPORT_FILE = "mutation_report.json"
MUTANTS_FILE = "all_mutants.json"

# TODO: Add a path/constant for your manual mutants, e.g.
# MANUAL_MUTANTS_FILE = "manual_mutants.json"
# and for your test suite file(s), e.g. TEST_FILE = "test_source_code.py"


# ---------------------------------------------------------
# LLM output cleanup helpers
# ---------------------------------------------------------
def clean_llm_output(content):
    content = re.sub(r"```json", "", content)
    content = re.sub(r"```", "", content)
    return content.strip()


def extract_json(content):
    start = content.find("[")
    end = content.rfind("]") + 1
    return content[start:end]


# ---------------------------------------------------------
# Automated mutant generation (LLM-based)
# ---------------------------------------------------------
def generate_mutants(full_code, target_section, num_mutants=5):
    """
    TODO: Build a prompt that asks the LLM to act as a mutation
    testing tool and generate `num_mutants` mutants that ONLY modify
    logic inside `target_section` of `full_code`.

    Requirements for the prompt:
    - Exactly `num_mutants` mutants
    - One small change per mutant (typical mutation operators: change
      a comparison operator, flip a boolean, change an arithmetic
      operator, off-by-one on a boundary, etc.)
    - Must remain valid Python syntax
    - Must return ONLY JSON, shaped like:
      [ {"id": 1, "description": "...", "code": "..."}, ... ]

    Then invoke the LLM, clean/parse the JSON response, and return
    the list of mutant dicts (or [] on failure).
    """
    prompt = f"""
    # TODO: write the mutation-generation prompt here, using
    # {target_section} and {full_code}, following the rules above.
    """

    response = llm.invoke(prompt)
    content = response.content

    content = clean_llm_output(content)
    content = extract_json(content)

    try:
        return json.loads(content)
    except Exception:
        print("Failed to parse LLM output for section:", target_section)
        return []


# ---------------------------------------------------------
# Manual mutants
# ---------------------------------------------------------
def load_manual_mutants():
    """
    TODO: Create at least 20 manual mutants (hand-written small code
    changes to the original source) and load them here — e.g. from a
    JSON file you author yourself, in the same shape as the automated
    mutants: [{"id": ..., "description": ..., "code": ...}, ...].
    These should be separate from (not overlapping with) the
    LLM-generated mutants, so you can compare manual vs automated
    mutation testing.
    """
    return []


# ---------------------------------------------------------
# Applying / running / restoring mutants
# ---------------------------------------------------------
def apply_mutant(code):
    with open(WORKING_FILE, "w") as f:
        f.write(code)


def run_tests():
    """
    Runs the test suite against the current WORKING_FILE.
    TODO: Make sure you've written unit tests (per the "Develop unit
    tests for the given software" feature) that pytest will discover
    and that meaningfully exercise the source code's behavior —
    otherwise mutants will "survive" even when they shouldn't.
    """
    try:
        result = subprocess.run(
            ["pytest", "-q"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return -1, "Timeout"


def restore_original():
    shutil.copyfile(ORIGINAL_FILE, WORKING_FILE)


def deduplicate_mutants(mutants):
    seen = set()
    unique = []

    for m in mutants:
        code = m.get("code", "")
        if code not in seen:
            seen.add(code)
            unique.append(m)

    return unique


# ---------------------------------------------------------
# Core mutant execution loop (shared by manual + automated)
# ---------------------------------------------------------
def execute_mutants(mutants):
    """
    TODO: Given a list of mutants (manual or automated), apply each
    one, run the test suite, classify it as killed / survived /
    invalid, restore the original file, and return the list of
    per-mutant result dicts. This logic currently lives inline inside
    run_pipeline() below for the automated mutants — consider
    factoring it out (as this function) so it can be reused for the
    manual mutant set too.
    """
    pass


# ---------------------------------------------------------
# Automated pipeline
# ---------------------------------------------------------
def run_pipeline():

    print("\nStarting Section-Based Mutation Pipeline...\n")

    with open(ORIGINAL_FILE, "r") as f:
        full_code = f.read()

    # TODO: Adjust these target sections to match the actual
    # functions/classes in the source code provided in resources.
    sections = [
        "TODO: e.g. ClassName.method_name",
        "TODO: another target section",
    ]

    all_mutants = []

    for section in sections:
        print(f"\nGenerating mutants for: {section}")

        mutants = generate_mutants(full_code, section, 5)

        print(f"Generated: {len(mutants)} mutants")

        all_mutants.extend(mutants)

        time.sleep(2)  # avoid rate limits

    all_mutants = deduplicate_mutants(all_mutants)

    print(f"\nTotal unique mutants: {len(all_mutants)}")

    with open(MUTANTS_FILE, "w") as f:
        json.dump(all_mutants, f, indent=4)

    print(f"Saved all mutants to {MUTANTS_FILE}")

    results = []
    killed = 0
    survived = 0
    invalid = 0

    for i, mutant in enumerate(all_mutants, 1):

        print(f"\n⚙️ Running Mutant {i}")

        try:
            apply_mutant(mutant["code"])
            returncode, output = run_tests()

            if returncode == -1:
                status = "invalid"
                invalid += 1

            elif returncode != 0:
                status = "killed"
                killed += 1

            else:
                status = "survived"
                survived += 1

        except Exception as e:
            status = "invalid"
            output = str(e)
            invalid += 1

        finally:
            restore_original()

        print(f"👉 Status: {status}")

        results.append({
            "id": mutant.get("id"),
            "description": mutant.get("description"),
            "status": status
        })

    total = len(all_mutants)
    score = (killed / total) * 100 if total else 0

    report = {
        "total": total,
        "killed": killed,
        "survived": survived,
        "invalid": invalid,
        "mutation_score": round(score, 2),
        "details": results
    }

    with open(REPORT_FILE, "w") as f:
        json.dump(report, f, indent=4)

    print("\n📊 FINAL REPORT")
    print(json.dumps(report, indent=4))

    # TODO: If mutation_score <= 95%, inspect `results` for
    # "survived" mutants, strengthen your unit tests to kill them,
    # and re-run the pipeline until you exceed the 95% target
    # (per the "Achieve a mutation score greater than 95%" feature).

    print("\n✅ Pipeline Complete!")


# ---------------------------------------------------------
# TODO: Manual mutation testing entry point
# ---------------------------------------------------------
def run_manual_pipeline():
    """
    TODO: Mirror run_pipeline() above, but using load_manual_mutants()
    instead of generate_mutants(). Produce a separate report (e.g.
    "manual_mutation_report.json") so manual vs automated mutation
    scores can be compared.
    """
    pass


if __name__ == "__main__":
    run_pipeline()
    # TODO: also call run_manual_pipeline() once implemented
