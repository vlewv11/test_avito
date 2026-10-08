from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from service.ml_topic_inference import MLTopicEnsemble


TOPIC_PRIORITY = [
    "06_illegal_content",
    "01_toxicity_threats",
    "02_pii",
    "05_adult_shocking",
    "04_fraud_manipulation",
    "03_spam_ads",
    "10_legal_reputation",
    "08_multimodal_consistency",
    "09_evasion_anomalies",
    "07_relevance_usefulness",
]

DECISION_SCORE = {"APPROVE": 0, "REVIEW": 1, "REJECT": 2}
PRIORITY_INDEX = {topic: idx for idx, topic in enumerate(TOPIC_PRIORITY)}

PHONE_RE = re.compile(r"(?:\+7|8)[\s\-\(\)]*\d[\d\s\-\(\)]{8,}")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+\.[a-z]{2,}", re.IGNORECASE)
URL_RE = re.compile(r"https?://", re.IGNORECASE)

TOPIC_ML_FALLBACK_REASON = {
    "01_toxicity_threats": "ML_TOPIC_01_SIGNAL",
    "02_pii": "ML_TOPIC_02_SIGNAL",
    "03_spam_ads": "ML_TOPIC_03_SIGNAL",
    "04_fraud_manipulation": "ML_TOPIC_04_SIGNAL",
    "05_adult_shocking": "ML_TOPIC_05_SIGNAL",
    "06_illegal_content": "ML_TOPIC_06_SIGNAL",
    "07_relevance_usefulness": "ML_TOPIC_07_SIGNAL",
    "08_multimodal_consistency": "ML_TOPIC_08_SIGNAL",
    "09_evasion_anomalies": "ML_TOPIC_09_SIGNAL",
    "10_legal_reputation": "ML_TOPIC_10_SIGNAL",
}


@dataclass
class TopicResult:
    topic_id: str
    decision: str
    reason_codes: list[str]
    confidence: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "topic_id": self.topic_id,
            "decision": self.decision,
            "reason_codes": self.reason_codes,
            "confidence": self.confidence,
        }


def normalize_text(text: str) -> str:
    normalized = text.lower().strip()
    normalized = normalized.replace("hxxp", "http").replace("[.]", ".")
    substitutions = {
        "0": "o",
        "1": "i",
        "3": "e",
        "4": "a",
        "5": "s",
        "7": "t",
        "@": "a",
    }
    for old, new in substitutions.items():
        normalized = normalized.replace(old, new)
    return normalized


def contains_any(text: str, phrases: list[str]) -> bool:
    return any(phrase in text for phrase in phrases)


def rule_illegal(text: str) -> TopicResult:
    reject_instructions = ["как обойти", "шаги", "обход блокиров", "инструкция"]
    reject_incitement = ["сделай закладку", "напади", "взломай", "укради"]
    reject_drugs = ["купить наркот", "продам наркот", "закладка"]
    reject_weapons = ["купить оруж", "продам оруж"]

    if contains_any(text, reject_instructions):
        return TopicResult("06_illegal_content", "REJECT", ["ILLEGAL_INSTRUCTIONS"], 0.93)
    if contains_any(text, reject_incitement):
        return TopicResult("06_illegal_content", "REJECT", ["ILLEGAL_INCITEMENT"], 0.93)
    if contains_any(text, reject_drugs):
        return TopicResult("06_illegal_content", "REJECT", ["ILLEGAL_DRUGS"], 0.94)
    if contains_any(text, reject_weapons):
        return TopicResult("06_illegal_content", "REJECT", ["ILLEGAL_WEAPONS"], 0.94)
    if "обход" in text or "обходы" in text:
        return TopicResult("06_illegal_content", "REVIEW", ["ILLEGAL_INSTRUCTIONS"], 0.65)
    return TopicResult("06_illegal_content", "APPROVE", [], 0.05)


def rule_toxicity(text: str, image_tokens: str) -> TopicResult:
    direct = ["сломаю", "убью", "изобью", "найду и"]
    indirect = ["тебя найдут", "тебе конец", "пожалеешь"]
    hate = ["по национальности", "ненавижу всех"]
    insult = ["мразь", "идиот", "урод", "тупой"]

    if contains_any(text, direct):
        return TopicResult("01_toxicity_threats", "REJECT", ["TOXIC_THREAT_DIRECT"], 0.95)
    if contains_any(text, hate):
        return TopicResult("01_toxicity_threats", "REJECT", ["TOXIC_HATE"], 0.93)
    if "toxic_text" in image_tokens:
        return TopicResult("01_toxicity_threats", "REVIEW", ["TOXIC_IMAGE_TEXT"], 0.75)
    if contains_any(text, indirect):
        return TopicResult("01_toxicity_threats", "REVIEW", ["TOXIC_THREAT_INDIRECT"], 0.78)
    if contains_any(text, insult):
        return TopicResult("01_toxicity_threats", "REVIEW", ["TOXIC_INSULT"], 0.7)
    return TopicResult("01_toxicity_threats", "APPROVE", [], 0.05)


def rule_pii(raw_text: str, normalized_text: str, image_tokens: str) -> TopicResult:
    if PHONE_RE.search(raw_text):
        return TopicResult("02_pii", "REJECT", ["PII_PHONE"], 0.96)
    if EMAIL_RE.search(raw_text) or "(at)" in normalized_text and "(dot)" in normalized_text:
        return TopicResult("02_pii", "REJECT", ["PII_EMAIL"], 0.94)
    if "карта" in normalized_text and re.search(r"\d{4}[\s\-*]?\d{4}", raw_text):
        return TopicResult("02_pii", "REJECT", ["PII_FINANCIAL"], 0.93)
    if "doc_image" in image_tokens:
        return TopicResult("02_pii", "REJECT", ["PII_DOCUMENT_IMAGE"], 0.9)
    return TopicResult("02_pii", "APPROVE", [], 0.05)


def rule_adult_shocking(text: str, image_tokens: str) -> TopicResult:
    if "adult_nudity" in image_tokens:
        return TopicResult("05_adult_shocking", "REJECT", ["ADULT_NUDITY"], 0.96)
    if "gore" in image_tokens:
        return TopicResult("05_adult_shocking", "REJECT", ["SHOCK_GORE_IMAGE"], 0.96)
    if contains_any(text, ["порно", "эротик", "шлюх", "проститут", "эскорт"]):
        return TopicResult("05_adult_shocking", "REJECT", ["ADULT_SEXUAL_TEXT"], 0.92)
    if contains_any(text, ["расчлен", "кровав", "внутренности"]):
        return TopicResult("05_adult_shocking", "REJECT", ["SHOCK_GORE_TEXT"], 0.92)
    return TopicResult("05_adult_shocking", "APPROVE", [], 0.05)


def rule_fraud(text: str) -> TopicResult:
    if "всем советую" in text and "лучший сервис" in text:
        return TopicResult("04_fraud_manipulation", "REJECT", ["FRAUD_TEMPLATE_CLUSTER"], 0.9)
    if "новый аккаунт" in text:
        return TopicResult("04_fraud_manipulation", "REVIEW", ["FRAUD_SUSPICIOUS_ACCOUNT"], 0.7)
    return TopicResult("04_fraud_manipulation", "APPROVE", [], 0.05)


def rule_spam(text: str) -> TopicResult:
    promo = ["промокод", "скидк", "реф", "ref=", "invite"]
    cta = ["переходи", "переходите", "покупай", "берите", "подписывайся"]

    if contains_any(text, promo) and contains_any(text, cta):
        return TopicResult("03_spam_ads", "REJECT", ["SPAM_REFERRAL"], 0.94)
    if len(URL_RE.findall(text)) >= 2:
        return TopicResult("03_spam_ads", "REJECT", ["SPAM_LINK_FARM"], 0.92)
    if contains_any(text, promo):
        return TopicResult("03_spam_ads", "REVIEW", ["AD_PROMOTION"], 0.68)
    return TopicResult("03_spam_ads", "APPROVE", [], 0.05)


def rule_legal_reputation(text: str) -> TopicResult:
    if "совершает преступления" in text:
        return TopicResult("10_legal_reputation", "REJECT", ["LEGAL_DEFAMATION_RISK"], 0.93)
    if contains_any(text, ["эти люди хуже", "по национальности все"]):
        return TopicResult("10_legal_reputation", "REJECT", ["LEGAL_DISCRIMINATION"], 0.92)
    if "похоже на мошенничество" in text:
        return TopicResult("10_legal_reputation", "REVIEW", ["LEGAL_REPUTATION_ESCALATION"], 0.72)
    return TopicResult("10_legal_reputation", "APPROVE", [], 0.05)


def rule_consistency(text: str, rating: int | None) -> TopicResult:
    if rating is None:
        return TopicResult("08_multimodal_consistency", "APPROVE", [], 0.05)

    negative = ["ужас", "ничего не работает", "плохо", "отврат"]
    positive = ["отлично", "супер", "прекрасно", "лучший"]

    if rating >= 5 and contains_any(text, negative):
        return TopicResult("08_multimodal_consistency", "REJECT", ["CONSISTENCY_TEXT_RATING_MISMATCH"], 0.9)
    if rating <= 1 and contains_any(text, positive):
        return TopicResult("08_multimodal_consistency", "REVIEW", ["CONSISTENCY_TEXT_RATING_MISMATCH"], 0.75)
    if "сарказм" in text:
        return TopicResult("08_multimodal_consistency", "REVIEW", ["CONSISTENCY_POTENTIAL_SARCASM"], 0.7)
    return TopicResult("08_multimodal_consistency", "APPROVE", [], 0.05)


def rule_evasion(text: str) -> TopicResult:
    if "hxxp" in text or "[.]" in text:
        return TopicResult("09_evasion_anomalies", "REJECT", ["EVASION_OBFUSCATED_LINK"], 0.95)
    if re.search(r"\b\w\s+\w\s+\w\b", text):
        return TopicResult("09_evasion_anomalies", "REVIEW", ["EVASION_WORD_SPLIT"], 0.66)
    emoji_count = sum(ch in "😀😄😆😂🤣😊😍🔥💥💣" for ch in text)
    if emoji_count >= 8:
        return TopicResult("09_evasion_anomalies", "REVIEW", ["EVASION_EMOJI_SPAM"], 0.61)
    return TopicResult("09_evasion_anomalies", "APPROVE", [], 0.05)


def rule_relevance(text: str, image_tokens: str) -> TopicResult:
    if contains_any(text, ["asdf", "qwe"]):
        return TopicResult("07_relevance_usefulness", "REJECT", ["REL_GARBAGE_TEXT"], 0.9)
    if contains_any(text, ["выборы", "политик", "митинг"]):
        return TopicResult("07_relevance_usefulness", "REJECT", ["REL_OFFTOPIC"], 0.86)
    if len(text.strip()) <= 5:
        return TopicResult("07_relevance_usefulness", "REVIEW", ["REL_LOW_INFORMATION"], 0.68)
    if "irrelevant_image" in image_tokens:
        return TopicResult("07_relevance_usefulness", "REVIEW", ["REL_IRRELEVANT_IMAGE"], 0.7)
    return TopicResult("07_relevance_usefulness", "APPROVE", [], 0.05)


def sort_topics_for_primary(topics: list[TopicResult]) -> list[TopicResult]:
    return sorted(topics, key=lambda t: PRIORITY_INDEX.get(t.topic_id, 999))


def aggregate(topic_results: list[TopicResult]) -> tuple[str, str | None, list[str]]:
    max_score = max(DECISION_SCORE[t.decision] for t in topic_results)
    decision = next(key for key, value in DECISION_SCORE.items() if value == max_score)

    if decision == "APPROVE":
        return decision, None, []

    same_severity = [
        t for t in topic_results if DECISION_SCORE[t.decision] == max_score and t.reason_codes
    ]
    same_severity = sort_topics_for_primary(same_severity)
    if not same_severity:
        return decision, None, []

    primary = same_severity[0].reason_codes[0]
    secondary: list[str] = []
    for topic in sort_topics_for_primary([t for t in topic_results if t.reason_codes]):
        for code in topic.reason_codes:
            if code != primary and code not in secondary:
                secondary.append(code)

    return decision, primary, secondary


def merge_reasons(rule_reasons: list[str], fallback_reason: str | None) -> list[str]:
    merged: list[str] = []
    for code in rule_reasons:
        if code not in merged:
            merged.append(code)
    if not merged and fallback_reason:
        merged.append(fallback_reason)
    return merged


def decide_by_thresholds(score: float, review_threshold: float, reject_threshold: float) -> str:
    if score >= reject_threshold:
        return "REJECT"
    if score >= review_threshold:
        return "REVIEW"
    return "APPROVE"


def build_rule_signals(review: dict[str, Any]) -> dict[str, TopicResult]:
    raw_text = str(review.get("text", ""))
    normalized_text = normalize_text(raw_text)
    rating = review.get("rating")
    image_tokens = " ".join(
        str(img.get("url", "")).lower() for img in review.get("images", []) if isinstance(img, dict)
    )

    return {
        "06_illegal_content": rule_illegal(normalized_text),
        "01_toxicity_threats": rule_toxicity(normalized_text, image_tokens),
        "02_pii": rule_pii(raw_text, normalized_text, image_tokens),
        "05_adult_shocking": rule_adult_shocking(normalized_text, image_tokens),
        "04_fraud_manipulation": rule_fraud(normalized_text),
        "03_spam_ads": rule_spam(normalized_text),
        "10_legal_reputation": rule_legal_reputation(normalized_text),
        "08_multimodal_consistency": rule_consistency(normalized_text, rating if isinstance(rating, int) else None),
        "09_evasion_anomalies": rule_evasion(normalized_text),
        "07_relevance_usefulness": rule_relevance(normalized_text, image_tokens),
    }


def classify_review(review: dict[str, Any], ml_ensemble: MLTopicEnsemble | None = None) -> dict[str, Any]:
    rule_signals = build_rule_signals(review)
    ml_scores = ml_ensemble.score_topics(review) if ml_ensemble else {}

    topic_results: list[TopicResult] = []
    for topic_id in TOPIC_PRIORITY:
        rule_signal = rule_signals[topic_id]
        ml_score = float(ml_scores.get(topic_id, 0.0))

        if ml_ensemble:
            review_threshold, reject_threshold = ml_ensemble.topic_thresholds(topic_id)
            ml_decision = decide_by_thresholds(ml_score, review_threshold, reject_threshold)
        else:
            ml_decision = "APPROVE"

        rule_decision = rule_signal.decision
        final_decision = rule_decision if DECISION_SCORE[rule_decision] >= DECISION_SCORE[ml_decision] else ml_decision

        if final_decision == "APPROVE":
            reason_codes: list[str] = []
        elif DECISION_SCORE[rule_decision] == DECISION_SCORE[final_decision]:
            reason_codes = merge_reasons(rule_signal.reason_codes, None)
        else:
            reason_codes = merge_reasons([], TOPIC_ML_FALLBACK_REASON.get(topic_id))

        confidence = round(max(ml_score, rule_signal.confidence), 4)

        topic_results.append(
            TopicResult(
                topic_id=topic_id,
                decision=final_decision,
                reason_codes=reason_codes,
                confidence=confidence,
            )
        )

    decision, primary, secondary = aggregate(topic_results)

    return {
        "decision": decision,
        "primary_reason_code": primary,
        "secondary_reason_codes": secondary,
        "topic_results": [result.as_dict() for result in topic_results],
    }
