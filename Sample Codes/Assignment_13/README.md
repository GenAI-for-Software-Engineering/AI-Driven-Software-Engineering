## What This Does

This pipeline automatically:
1. Reads a Python source file from the `transitions` repo
2. Asks Groq LLM (llama-3.3-70b-versatile) to write pytest tests for it
3. Runs those tests with `pytest`
4. Measures code coverage with `coverage.py`
5. Runs mutation testing with `mutmut`
6. Feeds the **surviving mutant diffs** back into the LLM with an augmented prompt
7. Gets better tests → repeats until mutation score ≥ 80% or max iterations reached
8. Saves a final report, metrics table, and all prompts used

```
┌──────────────────────────────────────────────────────────────┐
│  LOOP (up to N iterations, stops early if score ≥ 80%)      │
│                                                              │
│  TestGeneratorAgent  →  Generate pytest tests (Groq LLM)    │
│         ↓                                                    │
│  ExecutionAgent      →  Run pytest + measure coverage        │
│         ↓                                                    │
│  MutationAgent       →  Run mutmut, extract surviving diffs  │
│         ↓                                                    │
│  PromptRefinerAgent  →  Feed diffs back to LLM              │
│         ↓                                                    │
│  (repeat with augmented tests)                               │
└──────────────────────────────────────────────────────────────┘
```

---

## Your Folder Structure
```
main/
├── transitions/              ← cloned GitHub repo
│   ├── transitions/          ← actual Python package
│   │   ├── core.py           ← main file to test
│   │   ├── machine.py
│   │   └── ...
│   ├── tests/
│   ├── setup.py
│   └── ...
├── pipeline.py               ← main orchestrator  ← PUT THESE FILES HERE
├── groq_client.py
├── test_generator.py
├── execution_agent.py
├── mutation_agent.py
├── prompt_refiner.py
├── report.py
└── requirements.txt
```

---

## Step 0 — Find your target file

Open a terminal in `main` and run:
```bash
find transitions/transitions -name "*.py" | sort
```

You will see output like:
```
transitions/transitions/__init__.py
transitions/transitions/core.py
transitions/transitions/machine.py
transitions/transitions/extensions/factory.py
...
```

Pick a file. **Recommended for exam**: `transitions/transitions/core.py`  
If `core.py` is very large, use `transitions/transitions/machine.py` instead.

---

## Step 1 — Install Python dependencies for THIS pipeline

From the `main` folder (where `pipeline.py` lives):

```bash
pip install groq pytest pytest-cov coverage mutmut
```

---

## Step 2 — Install the `transitions` library itself

The generated tests need to import `transitions`. Install it in editable mode:

```bash
cd transitions
pip install -e .
cd ..
```

Verify it works:
```bash
python -c "import transitions; print('OK')"
```

---

## Step 3 — Get your Groq API key

1. Go to [https://console.groq.com/keys](https://console.groq.com/keys)
2. Sign in and create a new API key
3. Export it:

```bash
# On Mac/Linux:
export GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxx

# On Windows (Command Prompt):
set GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxx

# On Windows (PowerShell):
$env:GROQ_API_KEY="gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

---

## Step 4 — Run the pipeline

**Basic command** (from the `main` folder):

```bash
python pipeline.py --target transitions/core.py --repo ./transitions --iterations 3
```

**Full command with all options explained**:

```bash
python pipeline.py \
  --target transitions/core.py \   # path to Python file, relative to --repo
  --repo ./transitions \            # path to the cloned transitions repo
  --iterations 3 \                  # how many feedback loops to run
  --threshold 80 \                  # stop early if mutation score reaches 80%
  --output pipeline_output          # folder where results are saved
```

**Shorter alias versions** (same thing):

```bash
python pipeline.py -t transitions/core.py -r ./transitions -i 3 -s 80 -o pipeline_output
```

---

## What you will see during execution

```
═════════════════════════════════════════════════════════════════
  IT568 Q2 — LLM Test Generation & Mutation Testing Pipeline
  Target : transitions/core.py
  Repo   : /your/path/main/transitions
  Model  : llama-3.3-70b-versatile (Groq)
═════════════════════════════════════════════════════════════════

─────────────────────────────────────────────────────────────────
▶ ITERATION 1 / 3
─────────────────────────────────────────────────────────────────
[10:01:12] ▶ Step 1: Generating tests with LLM ...
[10:01:18] ✓ Tests written: 147 lines → test_generated.py
[10:01:18] ▶ Step 2: Running pytest ...
[10:01:22] ✓ pytest → 23 passed, 4 failed in 3.21s
[10:01:22] ▶ Step 3: Measuring code coverage ...
[10:01:24] ✓ Coverage: 43.2%  (210/486 lines)
[10:01:24] ▶ Step 4: Running mutmut (may take several minutes) ...
[10:06:45] ✓ Mutation score: 38.0%  (killed 19/50, survived 31)

  ──────────────────────────────────────────────────────────────
  Iter   Coverage   Mut Score   Killed   Survived   Test Lines
  ──────────────────────────────────────────────────────────────
     1      43.2%      38.0%       19         31          147
  ──────────────────────────────────────────────────────────────

─────────────────────────────────────────────────────────────────
▶ ITERATION 2 / 3
─────────────────────────────────────────────────────────────────
[10:06:45] ▶ Step 1: Generating tests with LLM ...   ← feeds surviving mutants to LLM
...
```

> ⚠️ **mutmut is slow** — each iteration's mutation step takes **5–15 minutes** for `core.py`.  
> Plan your exam time accordingly. Use a smaller file for faster runs.

---

## Output files (all inside `pipeline_output/`)

| File | Contents |
|------|----------|
| `test_final.py` | **Final merged test suite** — submit this |
| `tests_iter1.py` | Tests after iteration 1 |
| `tests_iter2.py` | Tests after iteration 2 |
| `tests_iter3.py` | Tests after iteration 3 |
| `metrics.json` | Raw metrics (coverage, mutation score, etc.) per iteration |
| `prompts_used.txt` | **Every prompt sent to the LLM** — required for exam submission |
| `final_report.txt` | Human-readable summary report |

---

## Using a faster/smaller target file

If `core.py` is too slow for the exam time limit, use a smaller module:

```bash
# Check file sizes first
wc -l transitions/transitions/*.py

# Then run on a smaller one
python pipeline.py -t transitions/machine.py -r ./transitions -i 2
```

---

## Agents and their roles

| Agent | File | Job |
|-------|------|-----|
| `TestGeneratorAgent` | `agents/test_generator.py` | Calls Groq LLM → writes initial pytest suite |
| `ExecutionAgent` | `agents/execution_agent.py` | Runs pytest, measures coverage.py |
| `MutationAgent` | `agents/mutation_agent.py` | Runs mutmut, extracts surviving mutant diffs |
| `PromptRefinerAgent` | `agents/prompt_refiner.py` | Builds augmented prompt with mutant diffs → calls Groq → new targeted tests |
| `PipelineOrchestrator` | `pipeline.py` | Drives the loop, merges tests, tracks metrics, saves outputs |

---

## How hallucination is prevented (exam justification)

### 1. System prompt format locking
Every system prompt starts with:
> *"Output ONLY raw Python code. No markdown, no fences, no explanations."*  
The code also strips any accidental markdown fences after the fact (defence in depth).

### 2. Grounding to source code
The actual source code is always injected into the user prompt. The system prompt says:
> *"Do NOT invent function names, class names, or attribute names that do not exist in the source code."*

### 3. Low temperature
`temperature=0.1` in `groq_client.py` makes the model conservative — it sticks to what it sees rather than hallucinating creative variations.

### 4. Single responsibility per agent
Each system prompt says *"Your ONLY job is..."* — a focused role reduces the chance the model drifts into doing something else.

### 5. Syntax validation + retry
`ast.parse()` checks every LLM response. If it has a `SyntaxError`, the pipeline retries with an error message appended to the prompt.

### 6. Augmented prompt explicitly includes metrics
The refiner prompt tells the model the **exact current coverage %**, **mutation score %**, and **which mutants survived** — anchoring it to facts rather than guesses.

---

## Common errors and fixes

### `ModuleNotFoundError: No module named 'transitions'`
```bash
cd transitions && pip install -e . && cd ..
```

### `ModuleNotFoundError: No module named 'groq'`
```bash
pip install groq
```

### `mutmut: command not found`
```bash
pip install mutmut
```

### `GROQ_API_KEY not set`
```bash
export GROQ_API_KEY=gsk_your_key_here
```

### mutmut runs but shows 0 mutants
mutmut needs to find the test file. Make sure `--repo` points to the repo root where `setup.py` is:
```bash
python pipeline.py -t transitions/core.py -r ./transitions -i 2
```

### Coverage is 0%
The `--cov` flag needs the file path relative to repo root. If it still fails, run manually:
```bash
cd transitions
python -m pytest ../pipeline_output/test_generated.py --cov=transitions/core.py --cov-report=term
```

---

## Full example from scratch (copy-paste sequence)

```bash
# 0. Make sure you're in main folder
cd main

# 1. Install pipeline dependencies
pip install groq pytest pytest-cov coverage mutmut

# 2. Install transitions library
cd transitions && pip install -e . && cd ..

# 3. Set API key
export GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxx

# 4. Run pipeline on core.py, 3 iterations, stop at 80% mutation score
python pipeline.py -t transitions/core.py -r ./transitions -i 3 -s 80 -o pipeline_output

# 5. View results
cat pipeline_output/final_report.txt
cat pipeline_output/prompts_used.txt
```

That's it. All output files for exam submission will be in `pipeline_output/`.
