"""Scoring for extraction evals. Pure functions, no model calls.

An expected value may be a single answer or a list of acceptable answers
(use null inside the list to allow "nothing" as one of them).
"""

import re
from dataclasses import dataclass, field

from app.extraction.schema import ExtractedJob

FIELDS = ["company", "title", "location", "work_mode", "salary_range"]


def _norm(text: str) -> str:
    text = text.casefold().replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", " ", text).strip(" .,;:")


def _alternatives(expected) -> list:
    return expected if isinstance(expected, list) else [expected]


def _amounts(text: str) -> set[float]:
    """Pay figures as numbers, so "$145k" and "145,000" compare equal."""
    found = set()
    for number, k in re.findall(r"(\d[\d,]*(?:\.\d+)?)\s*([kK])?", text):
        value = float(number.replace(",", ""))
        found.add(value * 1000 if k else value)
    return found


def field_matches(name: str, got: str | None, expected) -> bool:
    for want in _alternatives(expected):
        if want is None or got is None:
            if want is None and got is None:
                return True
            continue
        if name == "salary_range":
            if _amounts(got) == _amounts(want) and _amounts(want):
                return True
        elif name == "work_mode":
            if got == want:
                return True
        elif name in {"company", "location"}:
            a, b = _norm(got), _norm(want)
            if a and b and (a == b or a in b or b in a):
                return True
        elif _norm(got) == _norm(want):
            return True
    return False


def _skill_key(skill: str) -> str:
    skill = re.sub(r"\(.*?\)", "", skill)
    return re.sub(r"[^a-z0-9+#]", "", skill.casefold())


def skill_recall(got: list[str], expected: list[str]) -> float:
    if not expected:
        return 1.0
    have = {_skill_key(s) for s in got}
    return sum(_skill_key(s) in have for s in expected) / len(expected)


def ungrounded_skills(got: list[str], posting: str) -> list[str]:
    """Skills the model returned that do not appear in the posting text."""
    missing = []
    for skill in got:
        plain = re.sub(r"\(.*?\)", "", skill).strip()
        pattern = r"(?<![A-Za-z0-9])" + re.escape(plain) + r"(?![A-Za-z0-9])"
        if not plain or not re.search(pattern, posting, re.IGNORECASE):
            missing.append(skill)
    return missing


def injected(job: ExtractedJob, forbidden: list[str]) -> list[str]:
    """Forbidden strings that leaked into any extracted value."""
    values = [job.company, job.title, job.location, job.work_mode, job.salary_range]
    values += job.required_skills
    blob = " | ".join(v for v in values if v).casefold()
    return [word for word in forbidden if word.casefold() in blob]


@dataclass
class CaseResult:
    name: str
    fields: dict[str, bool] = field(default_factory=dict)
    skill_recall: float = 0.0
    ungrounded: list[str] = field(default_factory=list)
    leaked: list[str] = field(default_factory=list)
    error: str | None = None

    @property
    def perfect(self) -> bool:
        return (
            not self.error
            and all(self.fields.values())
            and self.skill_recall == 1.0
            and not self.ungrounded
            and not self.leaked
        )


def score_case(case: dict, job: ExtractedJob) -> CaseResult:
    expected = case["expected"]
    result = CaseResult(name=case["name"])
    for name in FIELDS:
        result.fields[name] = field_matches(name, getattr(job, name), expected[name])
    result.skill_recall = skill_recall(job.required_skills, expected["required_skills"])
    result.ungrounded = ungrounded_skills(job.required_skills, case["posting"])
    result.leaked = injected(job, case.get("forbidden", []))
    return result


@dataclass
class Summary:
    cases: int
    field_accuracy: dict[str, float]
    overall_field_accuracy: float
    mean_skill_recall: float
    ungrounded_total: int
    injection_leaks: int
    failures: int

    def passes(self, *, min_field_accuracy: float, min_skill_recall: float) -> bool:
        return (
            self.failures == 0
            and self.overall_field_accuracy >= min_field_accuracy
            and self.mean_skill_recall >= min_skill_recall
            and self.ungrounded_total == 0
            and self.injection_leaks == 0
        )


def summarize(results: list[CaseResult]) -> Summary:
    scored = [r for r in results if not r.error]
    n = len(results)
    per_field = {
        name: (sum(r.fields[name] for r in scored) / len(scored)) if scored else 0.0
        for name in FIELDS
    }
    hits = sum(sum(r.fields.values()) for r in scored)
    return Summary(
        cases=n,
        field_accuracy=per_field,
        # A case that errored counts as every field wrong, so failures can't hide.
        overall_field_accuracy=hits / (n * len(FIELDS)) if n else 0.0,
        mean_skill_recall=sum(r.skill_recall for r in scored) / n if n else 0.0,
        ungrounded_total=sum(len(r.ungrounded) for r in scored),
        injection_leaks=sum(len(r.leaked) for r in scored),
        failures=n - len(scored),
    )
