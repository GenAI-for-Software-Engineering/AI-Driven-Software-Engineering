"""
Report Generator
=================
Produces a human-readable .txt report summarising all iterations.
"""

from pathlib import Path
from datetime import datetime


def generate_report(metrics_log: list, output_dir: Path, target_file: str) -> Path:
    report_path = output_dir / "final_report.txt"
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        "=" * 65,
        "  IT568 Q2 — LLM Test Generation & Mutation Testing Pipeline",
        f"  Report generated: {now}",
        f"  Target file     : {target_file}",
        "=" * 65,
        "",
        "ITERATION-WISE METRICS",
        "─" * 65,
        f"{'Iter':>4}  {'Coverage':>9}  {'Mut Score':>10}  {'Killed':>7}  {'Survived':>9}  {'Test Lines':>10}",
        "─" * 65,
    ]

    for m in metrics_log:
        lines.append(
            f"{m['iteration']:>4}  "
            f"{m['coverage']:>8.1f}%  "
            f"{m['mutation_score']:>9.1f}%  "
            f"{m['killed']:>7}  "
            f"{m['survived']:>9}  "
            f"{m['test_lines']:>10}"
        )

    lines.append("─" * 65)

    if metrics_log:
        first = metrics_log[0]
        last = metrics_log[-1]

        lines += [
            "",
            "IMPROVEMENT SUMMARY",
            "─" * 65,
            f"  Coverage       : {first['coverage']:.1f}%  →  {last['coverage']:.1f}%  "
            f"(+{last['coverage'] - first['coverage']:.1f}%)",
            f"  Mutation Score : {first['mutation_score']:.1f}%  →  {last['mutation_score']:.1f}%  "
            f"(+{last['mutation_score'] - first['mutation_score']:.1f}%)",
            f"  Mutants Killed : {first['killed']}/{first['total']}  →  {last['killed']}/{last['total']}",
            f"  Iterations run : {last['iteration']}",
            "",
            "EXPLANATION OF IMPROVEMENTS PER ITERATION",
            "─" * 65,
        ]

        for i, m in enumerate(metrics_log):
            if i == 0:
                explanation = "Initial LLM-generated test suite covering normal, edge, and error cases."
            else:
                prev = metrics_log[i - 1]
                cov_delta = m['coverage'] - prev['coverage']
                mut_delta = m['mutation_score'] - prev['mutation_score']
                new_kills = m['killed'] - prev['killed']

                explanation = (
                    f"Augmented prompt fed {prev['survived']} surviving mutant diffs back to LLM. "
                    f"New tests targeted exact boundary conditions from mutant diffs. "
                    f"Coverage +{cov_delta:.1f}%, Mutation score +{mut_delta:.1f}%, "
                    f"{new_kills} additional mutants killed."
                )

            lines.append(f"  Iter {m['iteration']}: {explanation}")

    lines += [
        "",
        "OUTPUT FILES",
        "─" * 65,
        "  test_final.py     — Final merged test suite",
        "  tests_iter*.py    — Snapshot of tests after each iteration",
        "  metrics.json      — Raw metrics data",
        "  prompts_used.txt  — All LLM prompts used (exam submission)",
        "  final_report.txt  — This report",
        "",
        "=" * 65,
    ]

    report_path.write_text(
        "\n".join(lines),
        encoding="utf-8"
    )

    return report_path