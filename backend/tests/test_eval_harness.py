"""Tests for the eval scoring itself, so the yardstick can be trusted."""

import json
from pathlib import Path

import pytest

from app.extraction.schema import ExtractedJob
from evals.run_eval import CASES_FILE, OracleProvider, run
from evals.scoring import (
    field_matches,
    injected,
    score_case,
    skill_recall,
    summarize,
    ungrounded_skills,
)

CASES = json.loads(Path(CASES_FILE).read_text(encoding="utf-8"))


def test_every_case_is_well_formed():
    names = [c["name"] for c in CASES]
    assert len(names) == len(set(names))
    for case in CASES:
        assert {"company", "title", "location", "work_mode", "salary_range"} <= case[
            "expected"
        ].keys()
        assert isinstance(case["expected"]["required_skills"], list)
        # Expected skills must be verifiable from the posting text itself.
        assert ungrounded_skills(case["expected"]["required_skills"], case["posting"]) == [], case[
            "name"
        ]


def test_oracle_scores_perfectly():
    results = run(CASES, OracleProvider(CASES))
    summary = summarize(results)
    assert all(r.perfect for r in results), [r for r in results if not r.perfect]
    assert summary.overall_field_accuracy == 1.0
    assert summary.mean_skill_recall == 1.0
    assert summary.passes(min_field_accuracy=0.85, min_skill_recall=0.8)


class WrongProvider:
    """Always answers with the injected values from the prompt-injection case."""

    def complete_json(self, *, system, user):
        return json.dumps(
            {
                "company": "Evil Corp",
                "title": "CEO",
                "location": None,
                "work_mode": None,
                "salary_range": None,
                "required_skills": ["Hacking", "Quantum Basketweaving"],
            }
        )


def test_a_bad_model_fails_the_gate_and_leaks_are_caught():
    results = run(CASES, WrongProvider())
    summary = summarize(results)
    assert not summary.passes(min_field_accuracy=0.85, min_skill_recall=0.8)
    assert summary.injection_leaks >= 3
    assert summary.ungrounded_total > 0


def test_errored_cases_count_against_the_score():
    class Broken:
        def complete_json(self, *, system, user):
            return "not json"

    summary = summarize(run(CASES, Broken()))
    assert summary.failures == len(CASES)
    assert summary.overall_field_accuracy == 0.0
    assert not summary.passes(min_field_accuracy=0.0, min_skill_recall=0.0)


@pytest.mark.parametrize(
    ("name", "got", "expected", "ok"),
    [
        ("salary_range", "$145,000 - $170,000", "$145k-$170k per year", True),
        ("salary_range", "$145k-$180k", "$145k-$170k", False),
        ("salary_range", None, None, True),
        ("salary_range", "$100,000", None, False),
        ("company", "Initech", ["Initech Financial Group", "Initech"], True),
        ("company", "Evil Corp", "Initech", False),
        ("company", None, "Initech", False),
        ("location", "Charlotte, NC", ["New York, NY", "Charlotte, NC"], True),
        ("location", None, ["United States", None], True),
        ("location", "Austin, TX", ["Austin, Texas", "Austin, TX"], True),
        ("title", "Cloud Support Associate – Tier 2", "Cloud Support Associate - Tier 2", True),
        ("title", "Senior Engineer", "Engineer", False),
        ("work_mode", "hybrid", "hybrid", True),
        ("work_mode", "remote", "hybrid", False),
    ],
)
def test_field_matching(name, got, expected, ok):
    assert field_matches(name, got, expected) is ok


def test_skill_scoring():
    assert skill_recall(["python", "AWS (S3)"], ["Python", "AWS", "SQL"]) == pytest.approx(2 / 3)
    assert skill_recall([], []) == 1.0
    posting = "We use Python and TCP/IP. Go experience helps."
    assert ungrounded_skills(["Python", "TCP/IP", "Go", "Rust"], posting) == ["Rust"]
    # "Go" must not match inside another word.
    assert ungrounded_skills(["Go"], "We love good gophers.") == ["Go"]


def test_injection_detection_checks_every_field():
    job = ExtractedJob(company="Evil Corp", required_skills=["Hacking", "Python"])
    assert injected(job, ["Evil Corp", "Hacking", "CEO"]) == ["Evil Corp", "Hacking"]
    assert injected(ExtractedJob(title="Engineer"), ["Evil Corp"]) == []


def test_score_case_reports_misses():
    case = CASES[0]
    job = ExtractedJob(company="Wrong Inc", title=case["expected"]["title"])
    result = score_case(case, job)
    assert result.fields["company"] is False
    assert result.fields["title"] is True
    assert result.skill_recall == 0.0
    assert not result.perfect
