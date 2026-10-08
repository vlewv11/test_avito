from __future__ import annotations

from typing import Any

import pytest

from tests.scenario_data import (
    TOPIC_TO_PRIMARY_REASON,
    all_cases,
    borderline_cases,
    clean_cases,
    violation_cases,
)

ALLOWED_DECISIONS = {"APPROVE", "REVIEW", "REJECT"}
ALLOWED_STATUS = {"COMPLETED"}
REQUIRED_CASE_FIELDS = {
    "case_id",
    "topic_id",
    "title",
    "review",
    "expected_status",
    "expected_decision",
    "expected_primary_reason_code",
    "expected_secondary_reason_codes",
}


@pytest.mark.parametrize("case", all_cases, ids=[case["case_id"] for case in all_cases])
def test_case_structure(case: dict[str, Any]) -> None:
    assert set(case.keys()) == REQUIRED_CASE_FIELDS
    assert case["expected_status"] in ALLOWED_STATUS
    assert case["expected_decision"] in ALLOWED_DECISIONS
    assert isinstance(case["expected_secondary_reason_codes"], list)

    review_payload = case["review"]
    assert set(review_payload.keys()) == {"request_id", "review"}
    assert isinstance(review_payload["request_id"], str)
    assert review_payload["request_id"]

    review = review_payload["review"]
    assert isinstance(review, dict)
    assert {"review_id", "text"}.issubset(review.keys())
    assert isinstance(review["review_id"], str)
    assert isinstance(review["text"], str)
    assert review["review_id"]
    assert review["text"]


def test_violation_topics_covered_once() -> None:
    topic_ids = [case["topic_id"] for case in violation_cases]
    assert set(topic_ids) == set(TOPIC_TO_PRIMARY_REASON.keys())
    assert len(topic_ids) == len(set(topic_ids)) == 10


@pytest.mark.parametrize("case", violation_cases, ids=[case["case_id"] for case in violation_cases])
def test_violation_reason_matches_topic(case: dict[str, Any]) -> None:
    assert case["expected_decision"] == "REJECT"
    assert case["expected_primary_reason_code"] == TOPIC_TO_PRIMARY_REASON[case["topic_id"]]


@pytest.mark.parametrize("case", clean_cases, ids=[case["case_id"] for case in clean_cases])
def test_clean_cases_have_no_reasons(case: dict[str, Any]) -> None:
    assert case["expected_decision"] == "APPROVE"
    assert case["expected_primary_reason_code"] is None
    assert case["expected_secondary_reason_codes"] == []


@pytest.mark.parametrize("case", borderline_cases, ids=[case["case_id"] for case in borderline_cases])
def test_borderline_cases_are_review(case: dict[str, Any]) -> None:
    assert case["expected_decision"] == "REVIEW"
    assert isinstance(case["expected_primary_reason_code"], str)
