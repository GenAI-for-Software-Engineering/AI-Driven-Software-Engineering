"""
Agent 3: MutationAgent
=======================
Responsibility:
  - Run mutmut mutation testing on the target source file
  - Parse results (killed / survived / total / score)
  - Extract surviving mutant diffs to feed back into the prompt refiner

mutmut workflow:
  1. mutmut run --paths-to-mutate <file>  → runs all mutants
  2. mutmut results                        → summary
  3. mutmut show <id>                      → diff for each surviving mutant
"""

import re
import subprocess
from pathlib import Path


class MutationAgent:
    def __init__(self, repo_root: Path, target_file: str, test_file: Path):
        self.repo_root   = repo_root
        self.target_file = target_file   # relative path, e.g. "transitions/core.py"
        self.test_file   = test_file

    # ── main entry ────────────────────────────────────────────

    def run(self) -> dict:
        """
        Run mutmut and return structured results.
        Returns: { score, killed, survived, total, surviving_ids }
        """
        self._run_mutmut()
        return self._parse_results()

    # ── surviving diffs ───────────────────────────────────────

    def get_surviving_diffs(self, max_mutants: int = 10) -> str:
        """
        Return a text block of surviving mutant diffs,
        capped at max_mutants to keep prompt size reasonable.
        """
        surviving_ids = self._get_surviving_ids()[:max_mutants]
        if not surviving_ids:
            return "No surviving mutants found."

        diffs = []
        for mid in surviving_ids:
            try:
                result = subprocess.run(
                    ["python", "-m", "mutmut", "show", str(mid)],
                    cwd=self.repo_root,
                    capture_output=True, text=True, timeout=30,
                )
                if result.stdout.strip():
                    diffs.append(f"--- Mutant #{mid} ---\n{result.stdout.strip()}")
            except Exception:
                continue

        return "\n\n".join(diffs) if diffs else "Could not retrieve mutant diffs."

    # ── private ───────────────────────────────────────────────

    def _run_mutmut(self):
        """Run mutmut. It exits non-zero even on success, so we ignore returncode."""
        try:
            subprocess.run(
                [
                    "python", "-m", "mutmut", "run",
                    "--paths-to-mutate", self.target_file,
                    "--tests-dir", str(self.test_file.parent),
                ],
                cwd=self.repo_root,
                capture_output=True, text=True,
                timeout=600,   # 10 min max for large files
            )
        except subprocess.TimeoutExpired:
            print("  ⚠ mutmut timed out — partial results will be used")

    def _parse_results(self) -> dict:
        try:
            result = subprocess.run(
                ["python", "-m", "mutmut", "results"],
                cwd=self.repo_root,
                capture_output=True, text=True, timeout=30,
            )
            output = result.stdout + result.stderr
        except Exception as e:
            return {"score": 0.0, "killed": 0, "survived": 0, "total": 0, "surviving_ids": []}

        killed  = int((re.search(r"Killed:\s*(\d+)",   output) or [None, 0])[1])
        survived = int((re.search(r"Survived:\s*(\d+)", output) or [None, 0])[1])
        timeout  = int((re.search(r"Timeout:\s*(\d+)",  output) or [None, 0])[1])

        total = killed + survived + timeout
        score = (killed / total * 100) if total > 0 else 0.0

        return {
            "score"        : round(score, 1),
            "killed"       : killed,
            "survived"     : survived,
            "total"        : total,
            "surviving_ids": self._get_surviving_ids(),
        }

    def _get_surviving_ids(self) -> list[int]:
        try:
            result = subprocess.run(
                ["python", "-m", "mutmut", "results"],
                cwd=self.repo_root,
                capture_output=True, text=True, timeout=30,
            )
            # Lines like: "5) transitions/core.py"  or  "Survived mutants (5):"
            ids = re.findall(r"^\s*(\d+)\)", result.stdout, re.MULTILINE)
            return [int(i) for i in ids]
        except Exception:
            return []
