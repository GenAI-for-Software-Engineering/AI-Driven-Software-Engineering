"""
Agent 4: PromptRefinerAgent
============================
Responsibility:
  - Take surviving mutant diffs + current metrics
  - Build an augmented prompt that explicitly includes:
      * surviving mutants
      * current coverage %
      * current mutation score
  - Call Groq LLM to generate additional targeted tests

FIXES APPLIED:
  - System prompt and user prompt both explicitly state the correct import
    path (`from transitions.core import ...`) to prevent the LLM from
    generating un-importable code that causes "no tests ran".
  - Added same test_ function existence check as TestGeneratorAgent.
"""

import re
import ast
from groq_client import GroqClient


SYSTEM_PROMPT = """You are a Python test hardening expert specialising in mutation testing.
You will receive:
  1. A Python source file
  2. The current pytest test suite (with known coverage and mutation score)
  3. Diffs of surviving mutants — mutants the current tests FAILED to kill

Your ONLY job: write ADDITIONAL pytest test cases that specifically kill the surviving mutants.

════════════════════════════════════════════════════════════════
STRICT OUTPUT RULES
════════════════════════════════════════════════════════════════
1.  Output ONLY raw Python code. No markdown, no ``` fences, no prose.
2.  Write ONLY new test functions — do not repeat or modify existing tests.
3.  Every new test function MUST begin with "test_".
4.  CRITICAL IMPORT RULE:
      - Use:  from transitions.core import Machine, MachineError, State
      - Use:  from transitions import Machine
      - NEVER write `import core` or `from core import ...` — these fail at runtime.
5.  Above each new test, add a comment explaining which mutant it kills:
        # Kills mutant: <brief description of what was mutated>
6.  Use precise, exact assertion values — never assert "truthy" when you
    can assert the exact expected value.
7.  If a mutant changes an operator (e.g. > to >=, + to -), write a test
    that exercises the exact boundary where the operators differ.
8.  If a mutant removes a condition, write a test where that condition matters.
9.  Do NOT invent function names or attributes not present in the source code.
10. Tests must be deterministic and fully independent.
11. Your first line MUST be a comment: # Augmented tests — iteration N
════════════════════════════════════════════════════════════════
"""


class PromptRefinerAgent:
    MAX_RETRIES = 2

    def __init__(self, groq: GroqClient):
        self.groq = groq

    def augment(
        self,
        source_code: str,
        current_tests: str,
        surviving_diffs: str,
        coverage_pct: float,
        mutation_score: float,
        module_name: str,
    ) -> tuple[str, str]:
        """
        Build augmented prompt and generate additional tests.
        Returns (prompt_used, new_test_code).
        """
        prompt = self._build_prompt(
            source_code, current_tests, surviving_diffs,
            coverage_pct, mutation_score, module_name,
        )

        for attempt in range(self.MAX_RETRIES + 1):
            raw  = self.groq.chat(SYSTEM_PROMPT, prompt, max_tokens=4096)
            code = self._clean(raw)

            if not self._is_valid_python(code):
                prompt += "\n\nYour previous output had a Python syntax error. Output ONLY valid Python."
                continue

            # ✅ FIX: ensure at least one test_ function was generated
            if not re.search(r"^def test_", code, re.MULTILINE):
                prompt += (
                    "\n\nYour previous output contained no functions starting with 'test_'. "
                    "All test functions must begin with 'test_'. Rewrite accordingly."
                )
                continue

            return prompt, code

        return prompt, code

    # ── private ───────────────────────────────────────────────

    def _build_prompt(
        self,
        source_code: str,
        current_tests: str,
        surviving_diffs: str,
        coverage_pct: float,
        mutation_score: float,
        module_name: str,
    ) -> str:
        return f"""CURRENT TEST SUITE METRICS:
  Coverage       : {coverage_pct:.1f}%
  Mutation Score : {mutation_score:.1f}%

These metrics are NOT good enough. The surviving mutants below were NOT killed
by the current test suite. Your job is to write tests that kill them.

IMPORT REMINDER — use this exact import, do not use `import core`:
    from transitions.core import Machine, MachineError, State

SOURCE CODE (module: {module_name}):
```
{source_code[:4000]}
```
{'[truncated]' if len(source_code) > 4000 else ''}

EXISTING TESTS (do NOT repeat these):
```
{current_tests[:2000]}
```
{'[truncated]' if len(current_tests) > 2000 else ''}

SURVIVING MUTANT DIFFS (these are the mutants you must kill):
```diff
{surviving_diffs[:3000]}
```
{'[truncated]' if len(surviving_diffs) > 3000 else ''}

Now write additional pytest tests that kill the above surviving mutants.
Focus on exact boundary conditions and precise assertions.
Start with: # Augmented tests — iteration N
Then imports: import pytest / from transitions.core import Machine, MachineError, State
"""

    @staticmethod
    def _clean(code: str) -> str:
        code = re.sub(r"^```python\s*", "", code, flags=re.MULTILINE)
        code = re.sub(r"^```\s*$",      "", code, flags=re.MULTILINE)
        return code.strip()

    @staticmethod
    def _is_valid_python(code: str) -> bool:
        try:
            ast.parse(code)
            return True
        except SyntaxError:
            return False