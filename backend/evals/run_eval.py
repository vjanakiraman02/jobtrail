"""Measure extraction quality on the cases in cases.json.

Run from the backend/ folder:

    python -m evals.run_eval                 # uses the model configured in .env
    python -m evals.run_eval --oracle        # sanity-check the harness (should score 100%)
    python -m evals.run_eval --json out.json # also save a machine-readable report

Exit codes: 0 = thresholds met, 1 = below thresholds, 2 = model not configured.
"""

import argparse
import json
import sys
from pathlib import Path

from app.config import settings
from app.extraction.factory import ProviderConfigError, build_provider
from app.extraction.providers import ProviderError
from app.extraction.service import ExtractionError, extract_job
from evals.scoring import FIELDS, CaseResult, score_case, summarize

CASES_FILE = Path(__file__).with_name("cases.json")


class OracleProvider:
    """Answers every posting with its own expected values. Used to test the harness."""

    def __init__(self, cases: list[dict]):
        self._by_posting = {c["posting"]: c["expected"] for c in cases}

    def complete_json(self, *, system: str, user: str) -> str:
        for posting, expected in self._by_posting.items():
            if posting in user:
                first = {
                    k: (v[0] if isinstance(v, list) and k != "required_skills" else v)
                    for k, v in expected.items()
                }
                return json.dumps(first)
        raise ProviderError("oracle: unknown posting")


def run(cases: list[dict], provider) -> list[CaseResult]:
    results = []
    for case in cases:
        try:
            job = extract_job(case["posting"], provider)
            results.append(score_case(case, job))
        except (ExtractionError, ProviderError) as error:
            results.append(CaseResult(name=case["name"], error=str(error)))
    return results


def print_report(results: list[CaseResult], summary, label: str) -> None:
    print(f"\nExtraction eval: {label}\n")
    header = f"{'case':<30}" + "".join(f"{f[:8]:>10}" for f in FIELDS) + f"{'skills':>8}  notes"
    print(header)
    print("-" * len(header))
    for r in results:
        if r.error:
            print(f"{r.name:<30}ERROR: {r.error}")
            continue
        cells = "".join(f"{'ok' if r.fields[f] else 'MISS':>10}" for f in FIELDS)
        notes = []
        if r.ungrounded:
            notes.append(f"ungrounded: {', '.join(r.ungrounded)}")
        if r.leaked:
            notes.append(f"INJECTION LEAK: {', '.join(r.leaked)}")
        print(f"{r.name:<30}{cells}{r.skill_recall:>8.0%}  {'; '.join(notes)}")
    print()
    for name, value in summary.field_accuracy.items():
        print(f"  {name:<14}{value:>6.0%}")
    print(f"  overall field accuracy : {summary.overall_field_accuracy:.0%}")
    print(f"  mean skill recall      : {summary.mean_skill_recall:.0%}")
    print(f"  ungrounded skills      : {summary.ungrounded_total}")
    print(f"  injection leaks        : {summary.injection_leaks}")
    print(f"  cases that errored     : {summary.failures} of {summary.cases}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--oracle", action="store_true", help="use a perfect fake model")
    parser.add_argument("--json", metavar="FILE", help="write a JSON report to FILE")
    parser.add_argument("--min-field-accuracy", type=float, default=0.85)
    parser.add_argument("--min-skill-recall", type=float, default=0.8)
    args = parser.parse_args()

    cases = json.loads(CASES_FILE.read_text(encoding="utf-8"))
    if args.oracle:
        provider, label = OracleProvider(cases), "oracle (harness check)"
    else:
        try:
            provider = build_provider(settings)
        except (ProviderConfigError, ProviderError) as error:
            print(f"Cannot run against a real model: {error}")
            return 2
        label = f"{settings.llm_provider} / {settings.llm_model}"

    results = run(cases, provider)
    summary = summarize(results)
    print_report(results, summary, label)

    ok = summary.passes(
        min_field_accuracy=args.min_field_accuracy, min_skill_recall=args.min_skill_recall
    )
    print(f"\nResult: {'PASS' if ok else 'FAIL'}")

    if args.json:
        report = {
            "model": label,
            "summary": summary.__dict__,
            "cases": [r.__dict__ for r in results],
            "passed": ok,
        }
        Path(args.json).write_text(json.dumps(report, indent=2), encoding="utf-8")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
