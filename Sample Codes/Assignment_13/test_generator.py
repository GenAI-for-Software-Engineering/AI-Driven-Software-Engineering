"""
Agent 1: TestGeneratorAgent
============================
Responsibility: Use the Groq LLM to generate an initial pytest test suite
for a given Python source file.

FIXES APPLIED:
  - System prompt now explicitly instructs the model on how to import
    from the transitions package (the actual repo structure) — this is
    the root cause of "no tests ran": the LLM was generating
    `import core` instead of `from transitions import core` or
    `from transitions.core import Machine`, so pytest collected 0 tests
    because all imports failed silently.
  - Added import validation step that checks for at least one test_ function
    after cleaning, before returning.
"""

import re
import ast
from groq_client import GroqClient


SYSTEM_PROMPT = """You are a senior Python test engineer who specialises in pytest.
Your ONLY job is to write pytest unit tests for the Python source code given by the user.

════════════════════════════════════════════════════════════════
STRICT OUTPUT RULES — violating ANY rule produces invalid output
════════════════════════════════════════════════════════════════
1.  Output ONLY raw Python code. No markdown, no ``` fences, no explanations.
2.  Every test function MUST begin with "test_".
3.  The very first line of your output MUST be an import statement.
4.  CRITICAL IMPORT RULE for the transitions library:
      - Use:  from transitions.core import Machine, MachineError, State
      - Use:  from transitions import Machine
      - NEVER write: import core   ← this will fail (core is not a top-level module)
      - NEVER write: from core import ...  ← same reason
5.  Import ONLY from: the Python standard library, pytest, and the transitions package.
6.  Do NOT import any third-party library that is not already imported in the source code.
7.  Do NOT invent function names, class names, or attribute names that do not exist
    in the source code provided. If unsure, write a comment:
        # SKIPPED — could not verify existence of <name>
8.  Do NOT use unittest.mock or monkeypatching unless the source code itself
    does network calls or file I/O.
9.  Use pytest.raises() for tests that expect exceptions — never bare try/except.
10. Every test must be fully independent — no shared mutable state between tests.
11. Tests must be deterministic — no random data, no time.sleep(), no datetime.now().
12. Aim to cover: normal cases, boundary values, and invalid inputs.
════════════════════════════════════════════════════════════════
"""


class TestGeneratorAgent:
    MAX_RETRIES = 2

    def __init__(self, groq: GroqClient):
        self.groq = groq

    def generate_initial(self, source_code: str, module_name: str) -> tuple[str, str]:
        """
        Generate initial pytest suite for the given source.
        Returns (prompt_used, test_code).
        """
        prompt = self._build_prompt(source_code, module_name)

        for attempt in range(self.MAX_RETRIES + 1):
            raw  = self.groq.chat(SYSTEM_PROMPT, prompt, max_tokens=4096)
            code = self._clean(raw)

            if not self._is_valid_python(code):
                prompt += "\n\nYour previous output had a Python syntax error. Fix it and output ONLY valid Python."
                continue

            # ✅ FIX: also check that at least one test_ function was generated
            if not re.search(r"^def test_", code, re.MULTILINE):
                prompt += (
                    "\n\nYour previous output contained no functions starting with 'test_'. "
                    "pytest requires test functions to begin with 'test_'. "
                    "Rewrite with proper test_ function names."
                )
                continue

            return prompt, code

        # Last resort: return whatever we have
        return prompt, code

    # ── private helpers ───────────────────────────────────────

    def _build_prompt(self, source_code: str, module_name: str) -> str:
        return f"""Generate comprehensive pytest unit tests for the Python module "{module_name}".

IMPORTANT: This module is part of the 'transitions' package.
Correct import syntax:
    from transitions.core import Machine, MachineError, State
    from transitions import Machine
Do NOT write `import core` or `from core import ...` — those will fail.

SOURCE CODE TO TEST:
```python
{source_code[:6000]}
```
{'[Source truncated — focus on the visible functions and classes above]' if len(source_code) > 6000 else ''}

Requirements:
- Test every public function and method visible in the source above.
- Include tests for: normal inputs, edge cases (empty, None, zero, negative, large values).
- Include tests for invalid inputs that should raise exceptions.
- Do NOT test private methods (names starting with _).
- Begin with: import pytest
- Then: from transitions.core import Machine, MachineError, State
"""

    @staticmethod
    def _clean(code: str) -> str:
        """Strip accidental markdown fences the model might add despite instructions."""
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