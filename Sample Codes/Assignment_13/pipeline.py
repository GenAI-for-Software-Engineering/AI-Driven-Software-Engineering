"""
IT568 Q2 - LLM-based Automated Python Test Generation & Mutation Testing Pipeline
===================================================================================
University: Dhirubhai Ambani University (DA-IICT)
Course: IT568 GenAI for Software Engineering

Pipeline Flow:
Generate Tests -> Execute -> Measure Coverage -> Mutate -> Evaluate -> Augment Prompt -> Repeat

Agents:
  - TestGeneratorAgent   : Uses Groq LLM to write pytest test cases
  - ExecutionAgent       : Runs pytest, measures coverage
  - MutationAgent        : Runs mutmut, extracts surviving mutant diffs
  - PromptRefinerAgent   : Augments prompt with surviving mutants + metrics
  - PipelineOrchestrator : Drives the loop, tracks metrics, saves reports

FIXES APPLIED:
  1. Imports changed from `agents.X` to flat `X` — matches your file structure
     (all files are in the same directory, no agents/ subfolder)
  2. "no tests ran" is now handled: pipeline skips coverage+mutation and
     regenerates tests instead of recording 0/0 metrics and continuing
  3. test_file path is resolved to absolute before being passed to agents
"""

import os
import sys
import json
import re
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

from groq_client import GroqClient

# ✅ FIX: flat imports — no agents/ subfolder in your project
from test_generator import TestGeneratorAgent
from execution_agent import ExecutionAgent
from mutation_agent  import MutationAgent
from prompt_refiner  import PromptRefinerAgent
from report          import generate_report


# ---------------------------------------------------------------
# PIPELINE ORCHESTRATOR
# ---------------------------------------------------------------

class PipelineOrchestrator:
    def __init__(self, config: dict):
        self.config = config
        self.repo_root          = Path(config["repo_root"]).resolve()
        self.target_file        = config["target_file"]
        self.max_iterations     = config.get("max_iterations", 3)
        self.mutation_threshold = config.get("mutation_threshold", 80)
        self.output_dir         = Path(config.get("output_dir", "pipeline_output")).resolve()

        self.output_dir.mkdir(exist_ok=True)

        # ✅ FIX: resolve test_file to absolute path immediately
        self.test_file = (self.output_dir / "test_generated.py").resolve()

        # Clients
        api_key = config.get("groq_api_key") or os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not set. Add it to your .env file.")
        groq = GroqClient(api_key)

        # Agents — test_file is now always absolute
        self.test_gen  = TestGeneratorAgent(groq)
        self.executor  = ExecutionAgent(self.repo_root, self.test_file)
        self.mutator   = MutationAgent(self.repo_root, self.target_file, self.test_file)
        self.refiner   = PromptRefinerAgent(groq)

        self.metrics_log = []
        self.all_prompts = []

    # -- helpers -------------------------------------------------

    def log(self, msg: str, level: str = "INFO"):
        ts = datetime.now().strftime("%H:%M:%S")
        prefix = {
            "INFO": "  ",
            "STEP": ">>",
            "OK":   "[OK]",
            "WARN": "[WARN]",
            "ERR":  "[ERR]",
        }.get(level, "  ")
        print(f"[{ts}] {prefix} {msg}")

    def _read_source(self) -> str:
        src = self.repo_root / self.target_file
        if not src.exists():
            raise FileNotFoundError(f"Target source file not found: {src}")
        return src.read_text(encoding="utf-8")

    def _write_tests(self, code: str):
        self.test_file.write_text(code, encoding="utf-8")

    def _merge_tests(self, existing: str, new_code: str) -> str:
        """Append new tests, skipping functions whose names already exist."""
        existing_names = set(re.findall(r"^def (test_\w+)", existing, re.MULTILINE))
        lines = new_code.splitlines()
        out, skip = [], False
        for line in lines:
            m = re.match(r"^def (test_\w+)", line)
            if m:
                skip = m.group(1) in existing_names
            if not skip:
                out.append(line)
        separator = "\n\n# -- Augmented tests (surviving mutant kills) --\n"
        return existing + separator + "\n".join(out)

    def _print_metrics_table(self):
        hdr = (
            f"{'Iter':>4}  {'Coverage':>9}  {'Mut Score':>10}  "
            f"{'Killed':>7}  {'Survived':>9}  {'Test Lines':>10}"
        )
        bar = "-" * len(hdr)
        print(f"\n  {bar}")
        print(f"  {hdr}")
        print(f"  {bar}")
        for m in self.metrics_log:
            print(
                f"  {m['iteration']:>4}  "
                f"{m['coverage']:>8.1f}%  "
                f"{m['mutation_score']:>9.1f}%  "
                f"{m['killed']:>7}  "
                f"{m['survived']:>9}  "
                f"{m['test_lines']:>10}"
            )
        print(f"  {bar}\n")

    # -- main loop -----------------------------------------------

    def run(self):
        print("\n" + "=" * 65)
        print("  IT568 Q2 - LLM Test Generation & Mutation Testing Pipeline")
        print(f"  Target : {self.target_file}")
        print(f"  Repo   : {self.repo_root}")
        print(f"  Output : {self.output_dir}")
        print(f"  Model  : llama-3.3-70b-versatile (Groq)")
        print("=" * 65 + "\n")

        source_code   = self._read_source()
        module_name   = Path(self.target_file).stem
        current_tests = ""

        for iteration in range(1, self.max_iterations + 1):
            print(f"\n{'-' * 65}")
            self.log(f"ITERATION {iteration} / {self.max_iterations}", "STEP")
            print("-" * 65)

            # STEP 1: Generate / Augment Tests
            self.log("Step 1: Generating tests with LLM ...", "STEP")
            if iteration == 1:
                prompt, tests = self.test_gen.generate_initial(source_code, module_name)
            else:
                surviving_diffs = self.mutator.get_surviving_diffs()
                last = self.metrics_log[-1]
                prompt, tests = self.refiner.augment(
                    source_code=source_code,
                    current_tests=current_tests,
                    surviving_diffs=surviving_diffs,
                    coverage_pct=last["coverage"],
                    mutation_score=last["mutation_score"],
                    module_name=module_name,
                )

            self.all_prompts.append({"iteration": iteration, "prompt": prompt})

            if iteration == 1:
                current_tests = tests
            else:
                current_tests = self._merge_tests(current_tests, tests)

            self._write_tests(current_tests)
            test_lines = len(current_tests.splitlines())
            self.log(f"Tests written: {test_lines} lines -> {self.test_file}", "OK")

            # STEP 2: Run pytest
            self.log("Step 2: Running pytest ...", "STEP")
            test_result = self.executor.run_pytest()
            self.log(
                f"pytest -> {test_result['summary']}",
                "OK" if test_result["passed"] else "WARN",
            )

            # ✅ FIX: handle syntax errors
            if test_result.get("syntax_error"):
                self.log("Syntax error in generated tests — skipping iteration", "WARN")
                bad = self.output_dir / f"bad_tests_iter{iteration}.py"
                bad.write_text(current_tests, encoding="utf-8")
                continue

            # ✅ FIX: handle "no tests ran" — regenerate, don't record 0/0 and continue
            if test_result.get("no_tests"):
                self.log(
                    "pytest collected 0 tests — LLM test imports may be wrong. "
                    "Saving bad file and retrying next iteration.",
                    "WARN",
                )
                bad = self.output_dir / f"no_tests_iter{iteration}.py"
                bad.write_text(current_tests, encoding="utf-8")
                # Reset so next iteration regenerates from scratch
                current_tests = ""
                continue

            # STEP 3: Coverage
            self.log("Step 3: Measuring code coverage ...", "STEP")
            cov = self.executor.get_coverage(self.target_file)
            self.log(
                f"Coverage: {cov['percent']:.1f}%  ({cov['covered']}/{cov['total']} lines)",
                "OK",
            )

            # STEP 4: Mutation Testing
            self.log("Step 4: Running mutmut (may take several minutes) ...", "STEP")
            mut = self.mutator.run()
            self.log(
                f"Mutation score: {mut['score']:.1f}%  "
                f"(killed {mut['killed']}/{mut['total']}, survived {mut['survived']})",
                "OK",
            )

            # Record metrics
            entry = {
                "iteration":      iteration,
                "coverage":       cov["percent"],
                "mutation_score": mut["score"],
                "killed":         mut["killed"],
                "survived":       mut["survived"],
                "total":          mut["total"],
                "test_lines":     test_lines,
                "pytest_summary": test_result["summary"],
            }
            self.metrics_log.append(entry)
            self._print_metrics_table()

            # Save iteration snapshot
            snapshot = self.output_dir / f"tests_iter{iteration}.py"
            snapshot.write_text(current_tests, encoding="utf-8")

            # Check threshold
            if mut["score"] >= self.mutation_threshold:
                self.log(
                    f"Mutation score {mut['score']:.1f}% >= threshold "
                    f"{self.mutation_threshold}% — stopping early.",
                    "OK",
                )
                break

        # Final outputs
        final_test_file = self.output_dir / "test_final.py"
        final_test_file.write_text(current_tests, encoding="utf-8")
        self.log(f"Final test suite saved -> {final_test_file}", "OK")

        metrics_path = self.output_dir / "metrics.json"
        metrics_path.write_text(json.dumps(self.metrics_log, indent=2), encoding="utf-8")

        prompts_path = self.output_dir / "prompts_used.txt"
        with open(prompts_path, "w", encoding="utf-8") as f:
            for p in self.all_prompts:
                f.write(f"\n{'='*60}\nITERATION {p['iteration']} PROMPT\n{'='*60}\n")
                f.write(p["prompt"] + "\n")
        self.log(f"All prompts saved -> {prompts_path}", "OK")

        report_path = generate_report(self.metrics_log, self.output_dir, self.target_file)
        self.log(f"Report saved -> {report_path}", "OK")

        self._print_final_summary()

    def _print_final_summary(self):
        if not self.metrics_log:
            self.log("No metrics recorded — all iterations had import/syntax errors.", "WARN")
            return
        last = self.metrics_log[-1]
        print("\n" + "=" * 65)
        print("  FINAL RESULTS")
        print("=" * 65)
        print(f"  Coverage       : {last['coverage']:.1f}%")
        print(f"  Mutation Score : {last['mutation_score']:.1f}%")
        print(f"  Mutants Killed : {last['killed']} / {last['total']}")
        print(f"  Surviving      : {last['survived']}")
        print(f"  Iterations     : {last['iteration']}")
        print("=" * 65 + "\n")


# ---------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="IT568 Q2 - LLM Test Generation & Mutation Testing Pipeline"
    )
    parser.add_argument(
        "--target", "-t",
        default="transitions/core.py",
        help="Target Python file to test, relative to repo root (default: transitions/core.py)",
    )
    parser.add_argument(
        "--repo", "-r",
        default=".",
        help="Path to the cloned transitions repo root (default: current directory)",
    )
    parser.add_argument(
        "--iterations", "-i",
        type=int, default=3,
        help="Max iterations (default: 3)",
    )
    parser.add_argument(
        "--threshold", "-s",
        type=float, default=80.0,
        help="Stop early when mutation score exceeds this %% (default: 80)",
    )
    parser.add_argument(
        "--output", "-o",
        default="pipeline_output",
        help="Output directory for tests, metrics, reports (default: pipeline_output)",
    )
    args = parser.parse_args()

    config = {
        "target_file":        args.target,
        "repo_root":          args.repo,
        "max_iterations":     args.iterations,
        "mutation_threshold": args.threshold,
        "output_dir":         args.output,
    }

    orchestrator = PipelineOrchestrator(config)
    orchestrator.run()