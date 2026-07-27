"""
Agent 2: ExecutionAgent
========================
Responsibility:
  - Run the generated test file with pytest
  - Measure code coverage using coverage.py
  - Parse and return structured results

FIXES APPLIED (v2):
  1. pytest and coverage commands use the ABSOLUTE path to the test file
  2. cwd for all subprocess calls is repo_root
  3. --cov now uses MODULE DOT NOTATION (transitions.core) instead of file path
     → far more reliable with pytest-cov across all versions
  4. --cov-report=json now has an EXPLICIT output path (no more guessing location)
  5. 'passed' detection correctly checks returncode AND output
  6. 'no tests ran' is treated as a failure, not a pass
  7. Added pytest-cov install check with helpful error message
"""

import json
import subprocess
from pathlib import Path


def _file_path_to_module(target_file: str) -> str:
    """
    Convert a file path like 'transitions/core.py' to module notation 'transitions.core'.
    pytest-cov --cov= works reliably with module dot notation, NOT file paths.
    """
    return target_file.replace("\\", "/").removesuffix(".py").replace("/", ".")


class ExecutionAgent:
    def __init__(self, repo_root: Path, test_file: Path):
        self.repo_root = Path(repo_root).resolve()
        self.test_file = Path(test_file).resolve()   # always absolute

    # -- pytest --------------------------------------------------

    def run_pytest(self) -> dict:
        """
        Run pytest on the generated test file.
        Returns a dict with keys: passed, failed, errors, summary, syntax_error, output
        """
        cmd = [
            "python", "-m", "pytest",
            str(self.test_file),          # absolute path — never "not found"
            "-v", "--tb=short", "--no-header", "-q",
        ]
        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.repo_root),  # source lives here
                capture_output=True,
                text=True,
                timeout=180,
            )
        except subprocess.TimeoutExpired:
            return {
                "passed": False, "syntax_error": False,
                "summary": "pytest timed out", "output": "", "returncode": -1,
            }

        output = result.stdout + result.stderr

        # Detect syntax / indent errors in generated tests
        syntax_error = "SyntaxError" in output or "IndentationError" in output

        summary = self._parse_summary(output)

        # "no tests ran" must NOT be treated as passing
        no_tests = "no tests ran" in output.lower()

        # passed only if returncode=0 AND at least one test collected
        passed = (
            result.returncode == 0
            and not syntax_error
            and not no_tests
            and "passed" in output
        )

        if no_tests:
            print(f"    [WARN] pytest collected 0 tests — check imports in test file")

        return {
            "passed":       passed,
            "no_tests":     no_tests,
            "syntax_error": syntax_error,
            "summary":      summary,
            "output":       output,
            "returncode":   result.returncode,
        }

    # -- coverage ------------------------------------------------

    def get_coverage(self, target_file: str) -> dict:
        """
        Run pytest with coverage on the target file.

        KEY FIXES vs original:
          1. Uses MODULE DOT NOTATION for --cov (e.g. transitions.core not transitions/core.py)
             → pytest-cov resolves module paths reliably; file paths are version-dependent
          2. Passes EXPLICIT output path to --cov-report=json:<path>
             → no more relying on "current directory" which can vary
        """
        # FIX 1: convert file path to module dot notation
        cov_module = _file_path_to_module(target_file)

        # FIX 2: explicit output path so we always find the file
        cov_json_path = self.repo_root / "coverage.json"
        if cov_json_path.exists():
            cov_json_path.unlink()

        cmd = [
            "python", "-m", "pytest",
            str(self.test_file),                            # absolute path
            f"--cov={cov_module}",                          # FIX 1: module notation
            f"--cov-report=json:{cov_json_path}",           # FIX 2: explicit path
            "--cov-report=term-missing",
            "--cov-fail-under=0",                           # never fail just due to coverage threshold
            "-q", "--no-header",
        ]

        print(f"    [DEBUG] Coverage cmd : {' '.join(str(c) for c in cmd)}")
        print(f"    [DEBUG] Running in   : {self.repo_root}")
        print(f"    [DEBUG] Cov module   : {cov_module}  (converted from '{target_file}')")

        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.repo_root),
                capture_output=True,
                text=True,
                timeout=180,
            )
        except subprocess.TimeoutExpired:
            print("    [DEBUG] Coverage timed out")
            return {"percent": 0.0, "covered": 0, "total": 0, "missing_lines": 0}

        output = result.stdout + result.stderr
        print(f"    [DEBUG] Coverage output (first 800 chars):\n{output[:800]}")

        # Check if pytest-cov is even installed
        if "no module named pytest_cov" in output.lower() or \
           "unrecognized arguments: --cov" in output.lower():
            print("    [ERROR] pytest-cov is NOT installed!")
            print("    [ERROR] Fix: pip install pytest-cov")
            return {"percent": 0.0, "covered": 0, "total": 0, "missing_lines": 0,
                    "error": "pytest-cov not installed"}

        if cov_json_path.exists():
            try:
                data   = json.loads(cov_json_path.read_text(encoding="utf-8"))
                totals = data.get("totals", {})
                pct    = totals.get("percent_covered", 0.0)
                print(f"    [DEBUG] coverage.json found -> {pct:.1f}%")
                return {
                    "percent":       pct,
                    "covered":       totals.get("covered_lines", 0),
                    "total":         totals.get("num_statements", 0),
                    "missing_lines": totals.get("missing_lines", 0),
                }
            except Exception as e:
                print(f"    [DEBUG] Failed to parse coverage.json: {e}")
        else:
            print(f"    [DEBUG] coverage.json NOT found at {cov_json_path}")
            print(f"    [DEBUG] Trying fallback: cover entire 'transitions' package")
            return self._fallback_coverage()

        return {"percent": 0.0, "covered": 0, "total": 0, "missing_lines": 0}

    def _fallback_coverage(self) -> dict:
        """Fallback: measure coverage of the entire transitions package."""
        cov_json_path = self.repo_root / "coverage_fallback.json"
        if cov_json_path.exists():
            cov_json_path.unlink()

        cmd = [
            "python", "-m", "pytest",
            str(self.test_file),
            "--cov=transitions",
            f"--cov-report=json:{cov_json_path}",   # FIX: explicit path here too
            "--cov-report=term-missing",
            "--cov-fail-under=0",
            "-q", "--no-header",
        ]

        try:
            result = subprocess.run(
                cmd,
                cwd=str(self.repo_root),
                capture_output=True,
                text=True,
                timeout=180,
            )
        except subprocess.TimeoutExpired:
            return {"percent": 0.0, "covered": 0, "total": 0, "missing_lines": 0}

        output = result.stdout + result.stderr
        print(f"    [DEBUG] Fallback coverage output:\n{output[:800]}")

        if cov_json_path.exists():
            try:
                data   = json.loads(cov_json_path.read_text(encoding="utf-8"))
                totals = data.get("totals", {})
                pct    = totals.get("percent_covered", 0.0)
                print(f"    [DEBUG] Fallback coverage.json -> {pct:.1f}%")
                return {
                    "percent":       pct,
                    "covered":       totals.get("covered_lines", 0),
                    "total":         totals.get("num_statements", 0),
                    "missing_lines": totals.get("missing_lines", 0),
                }
            except Exception as e:
                print(f"    [DEBUG] Fallback parse error: {e}")

        return {"percent": 0.0, "covered": 0, "total": 0, "missing_lines": 0}

    # -- helpers -------------------------------------------------

    @staticmethod
    def _parse_summary(output: str) -> str:
        for line in reversed(output.splitlines()):
            line = line.strip()
            if any(kw in line for kw in ("passed", "failed", "error", "no tests")):
                return line
        return "no summary found"