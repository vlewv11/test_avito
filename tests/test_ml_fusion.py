from __future__ import annotations

from typing import Any

from service.moderation_engine import classify_review


class StubEnsemble:
    def __init__(self, scores: dict[str, float]) -> None:
        self._scores = scores

    def score_topics(self, review: dict[str, Any]) -> dict[str, float]:
        return self._scores

    def topic_thresholds(self, topic_id: str) -> tuple[float, float]:
        return 0.6, 0.85

    def reason_candidates(self, topic_id: str) -> tuple[str, str]:
        return f"{topic_id}_ML_REVIEW", f"{topic_id}_ML_REJECT"


def test_rules_boost_recall_even_with_low_ml_score() -> None:
    review = {"review_id": "r1", "text": "как обойти блокировку", "rating": 5}
    ensemble = StubEnsemble({"06_illegal_content": 0.01})
    result = classify_review(review, ensemble)

    assert result["decision"] == "REJECT"
    assert result["primary_reason_code"] == "ILLEGAL_INSTRUCTIONS"


def test_ml_score_triggers_fallback_reason_when_rules_silent() -> None:
    review = {"review_id": "r2", "text": "Доставка нормальная", "rating": 5}
    ensemble = StubEnsemble({"07_relevance_usefulness": 0.7})
    result = classify_review(review, ensemble)

    topic = next(t for t in result["topic_results"] if t["topic_id"] == "07_relevance_usefulness")
    assert topic["decision"] == "REVIEW"
    assert topic["reason_codes"] == ["ML_TOPIC_07_SIGNAL"]


def test_emoji_spam_has_correct_reason_code() -> None:
    review = {"review_id": "r-emoji-spam", "text": "🔥🔥🔥🔥🔥🔥🔥🔥", "rating": 5}
    result = classify_review(review, None)

    assert result["decision"] == "REVIEW"
    assert result["primary_reason_code"] == "EVASION_EMOJI_SPAM"

    topic = next(
        topic
        for topic in result["topic_results"]
        if topic["topic_id"] == "09_evasion_anomalies"
    )
    assert topic["decision"] == "REVIEW"
    assert topic["reason_codes"] == ["EVASION_EMOJI_SPAM"]


def test_neutral_crime_mention_is_not_rejected_as_defamation() -> None:
    review = {
        "review_id": "r-legal-neutral",
        "text": "В статье обсуждается статистика преступлений за прошлый год",
        "rating": 4,
    }
    result = classify_review(review, None)

    assert result["decision"] == "APPROVE"
    assert result["primary_reason_code"] is None


def test_categorical_crime_accusation_is_still_rejected() -> None:
    review = {
        "review_id": "r-legal-accusation",
        "text": "Эта компания совершает преступления, это факт",
        "rating": 1,
    }
    result = classify_review(review, None)

    assert result["decision"] == "REJECT"
    assert result["primary_reason_code"] == "LEGAL_DEFAMATION_RISK"


def test_positive_text_with_rating_two_is_not_flagged_as_mismatch() -> None:
    review = {
        "review_id": "r-consistency-rating-two",
        "text": "Всё отлично, товар полностью соответствует описанию",
        "rating": 2,
    }
    result = classify_review(review, None)

    assert result["decision"] == "APPROVE"
    assert result["primary_reason_code"] is None


def test_positive_text_with_rating_one_is_still_reviewed() -> None:
    review = {
        "review_id": "r-consistency-rating-one",
        "text": "Всё отлично, товар полностью соответствует описанию",
        "rating": 1,
    }
    result = classify_review(review, None)

    assert result["decision"] == "REVIEW"
    assert result["primary_reason_code"] == "CONSISTENCY_TEXT_RATING_MISMATCH"


def test_ml_alone_can_reject_when_rule_silent() -> None:
    review = {"review_id": "r-ml-only", "text": "Доставка нормальная", "rating": 5}
    ensemble = StubEnsemble({"07_relevance_usefulness": 0.9})
    result = classify_review(review, ensemble)

    topic = next(t for t in result["topic_results"] if t["topic_id"] == "07_relevance_usefulness")
    assert topic["decision"] == "REJECT"
    assert topic["reason_codes"] == ["ML_TOPIC_07_SIGNAL"]


def test_rule_review_does_not_become_reject_via_ml_addition() -> None:
    review = {"review_id": "r-indep", "text": "новый аккаунт", "rating": 5}
    ensemble = StubEnsemble({"04_fraud_manipulation": 0.5})
    result = classify_review(review, ensemble)

    topic = next(t for t in result["topic_results"] if t["topic_id"] == "04_fraud_manipulation")
    assert topic["decision"] == "REVIEW"
    assert "FRAUD_SUSPICIOUS_ACCOUNT" in topic["reason_codes"]
