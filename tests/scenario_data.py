from __future__ import annotations

from typing import Any

TOPIC_TO_PRIMARY_REASON = {
    "01_toxicity_threats": "TOXIC_THREAT_DIRECT",
    "02_pii": "PII_PHONE",
    "03_spam_ads": "SPAM_REFERRAL",
    "04_fraud_manipulation": "FRAUD_TEMPLATE_CLUSTER",
    "05_adult_shocking": "ADULT_NUDITY",
    "06_illegal_content": "ILLEGAL_INSTRUCTIONS",
    "07_relevance_usefulness": "REL_GARBAGE_TEXT",
    "08_multimodal_consistency": "CONSISTENCY_TEXT_RATING_MISMATCH",
    "09_evasion_anomalies": "EVASION_OBFUSCATED_LINK",
    "10_legal_reputation": "LEGAL_DEFAMATION_RISK",
}

violation_cases: list[dict[str, Any]] = [
    {
        "case_id": "V01",
        "topic_id": "01_toxicity_threats",
        "title": "Прямая угроза физического вреда",
        "review": {
            "request_id": "req-v01",
            "review": {
                "review_id": "rvw-v01",
                "text": "Я тебя найду и сломаю тебе руки",
                "rating": 1,
            },
        },
        "expected_status": "COMPLETED",
        "expected_decision": "REJECT",
        "expected_primary_reason_code": "TOXIC_THREAT_DIRECT",
        "expected_secondary_reason_codes": [],
    },
    {
        "case_id": "V02",
        "topic_id": "02_pii",
        "title": "Полный телефон в тексте",
        "review": {
            "request_id": "req-v02",
            "review": {
                "review_id": "rvw-v02",
                "text": "Звоните +7 999 123-45-67, решим вопрос",
                "rating": 5,
            },
        },
        "expected_status": "COMPLETED",
        "expected_decision": "REJECT",
        "expected_primary_reason_code": "PII_PHONE",
        "expected_secondary_reason_codes": [],
    },
    {
        "case_id": "V03",
        "topic_id": "03_spam_ads",
        "title": "Реферальная реклама с CTA",
        "review": {
            "request_id": "req-v03",
            "review": {
                "review_id": "rvw-v03",
                "text": "Переходите по ссылке и берите со скидкой, промокод IVAN10",
                "rating": 5,
            },
        },
        "expected_status": "COMPLETED",
        "expected_decision": "REJECT",
        "expected_primary_reason_code": "SPAM_REFERRAL",
        "expected_secondary_reason_codes": [],
    },
    {
        "case_id": "V04",
        "topic_id": "04_fraud_manipulation",
        "title": "Шаблонный кластер отзывов",
        "review": {
            "request_id": "req-v04",
            "review": {
                "review_id": "rvw-v04",
                "text": "Идеально! Всем советую, лучший сервис",
                "rating": 5,
            },
        },
        "expected_status": "COMPLETED",
        "expected_decision": "REJECT",
        "expected_primary_reason_code": "FRAUD_TEMPLATE_CLUSTER",
        "expected_secondary_reason_codes": [],
    },
    {
        "case_id": "V05",
        "topic_id": "05_adult_shocking",
        "title": "Явный adult-контент по изображению",
        "review": {
            "request_id": "req-v05",
            "review": {
                "review_id": "rvw-v05",
                "text": "Смотрите фото",
                "images": [{"url": "https://cdn.example/adult_nudity.jpg", "mime_type": "image/jpeg"}],
            },
        },
        "expected_status": "COMPLETED",
        "expected_decision": "REJECT",
        "expected_primary_reason_code": "ADULT_NUDITY",
        "expected_secondary_reason_codes": [],
    },
    {
        "case_id": "V06",
        "topic_id": "06_illegal_content",
        "title": "Инструкции по обходу закона",
        "review": {
            "request_id": "req-v06",
            "review": {
                "review_id": "rvw-v06",
                "text": "Вот шаги как обойти блокировку: сначала ..., потом ...",
                "rating": 1,
            },
        },
        "expected_status": "COMPLETED",
        "expected_decision": "REJECT",
        "expected_primary_reason_code": "ILLEGAL_INSTRUCTIONS",
        "expected_secondary_reason_codes": [],
    },
    {
        "case_id": "V07",
        "topic_id": "07_relevance_usefulness",
        "title": "Мусорный бессодержательный текст",
        "review": {
            "request_id": "req-v07",
            "review": {
                "review_id": "rvw-v07",
                "text": "asdf qwe 123 !!!",
                "rating": 3,
            },
        },
        "expected_status": "COMPLETED",
        "expected_decision": "REJECT",
        "expected_primary_reason_code": "REL_GARBAGE_TEXT",
        "expected_secondary_reason_codes": [],
    },
    {
        "case_id": "V08",
        "topic_id": "08_multimodal_consistency",
        "title": "Сильное противоречие текста и рейтинга",
        "review": {
            "request_id": "req-v08",
            "review": {
                "review_id": "rvw-v08",
                "text": "Ужасный сервис, ничего не работает",
                "rating": 5,
            },
        },
        "expected_status": "COMPLETED",
        "expected_decision": "REJECT",
        "expected_primary_reason_code": "CONSISTENCY_TEXT_RATING_MISMATCH",
        "expected_secondary_reason_codes": [],
    },
    {
        "case_id": "V09",
        "topic_id": "09_evasion_anomalies",
        "title": "Обфусцированная вредная ссылка",
        "review": {
            "request_id": "req-v09",
            "review": {
                "review_id": "rvw-v09",
                "text": "Переходи hxxp://bad[[.]]site для обходов",
                "rating": 5,
            },
        },
        "expected_status": "COMPLETED",
        "expected_decision": "REJECT",
        "expected_primary_reason_code": "EVASION_OBFUSCATED_LINK",
        "expected_secondary_reason_codes": ["ILLEGAL_INSTRUCTIONS"],
    },
    {
        "case_id": "V10",
        "topic_id": "10_legal_reputation",
        "title": "Категоричное обвинение без доказательств",
        "review": {
            "request_id": "req-v10",
            "review": {
                "review_id": "rvw-v10",
                "text": "Эта компания совершает преступления, это факт",
                "rating": 1,
            },
        },
        "expected_status": "COMPLETED",
        "expected_decision": "REJECT",
        "expected_primary_reason_code": "LEGAL_DEFAMATION_RISK",
        "expected_secondary_reason_codes": [],
    },
]

clean_cases: list[dict[str, Any]] = [
    {
        "case_id": "C01",
        "topic_id": "clean",
        "title": "Нейтральный детальный отзыв",
        "review": {
            "request_id": "req-c01",
            "review": {
                "review_id": "rvw-c01",
                "text": "Доставили за два дня, товар соответствует описанию, упаковка целая",
                "rating": 5,
            },
        },
        "expected_status": "COMPLETED",
        "expected_decision": "APPROVE",
        "expected_primary_reason_code": None,
        "expected_secondary_reason_codes": [],
    },
    {
        "case_id": "C02",
        "topic_id": "clean",
        "title": "Короткий, но предметный отзыв",
        "review": {
            "request_id": "req-c02",
            "review": {
                "review_id": "rvw-c02",
                "text": "Хороший товар, работает стабильно",
                "rating": 5,
            },
        },
        "expected_status": "COMPLETED",
        "expected_decision": "APPROVE",
        "expected_primary_reason_code": None,
        "expected_secondary_reason_codes": [],
    },
    {
        "case_id": "C03",
        "topic_id": "clean",
        "title": "Смешанный фидбек с объяснением",
        "review": {
            "request_id": "req-c03",
            "review": {
                "review_id": "rvw-c03",
                "text": "Товар отличный, но доставка задержалась на день",
                "rating": 4,
            },
        },
        "expected_status": "COMPLETED",
        "expected_decision": "APPROVE",
        "expected_primary_reason_code": None,
        "expected_secondary_reason_codes": [],
    },
    {
        "case_id": "C04",
        "topic_id": "clean",
        "title": "Отзыв с изображением по теме",
        "review": {
            "request_id": "req-c04",
            "review": {
                "review_id": "rvw-c04",
                "text": "На фото видно упаковку и состояние товара после доставки",
                "rating": 4,
                "images": [{"url": "https://cdn.example/review_ok_1.jpg", "mime_type": "image/jpeg"}],
            },
        },
        "expected_status": "COMPLETED",
        "expected_decision": "APPROVE",
        "expected_primary_reason_code": None,
        "expected_secondary_reason_codes": [],
    },
    {
        "case_id": "C05",
        "topic_id": "clean",
        "title": "Критика сервиса без оскорблений",
        "review": {
            "request_id": "req-c05",
            "review": {
                "review_id": "rvw-c05",
                "text": "Поддержка отвечает медленно, но проблему в итоге решили",
                "rating": 3,
            },
        },
        "expected_status": "COMPLETED",
        "expected_decision": "APPROVE",
        "expected_primary_reason_code": None,
        "expected_secondary_reason_codes": [],
    },
]

borderline_cases: list[dict[str, Any]] = [
    {
        "case_id": "B01",
        "topic_id": "01_toxicity_threats",
        "title": "Косвенная угроза без явного обещания вреда",
        "review": {
            "request_id": "req-b01",
            "review": {
                "review_id": "rvw-b01",
                "text": "Тебя найдут, лучше молчи",
                "rating": 1,
            },
        },
        "expected_status": "COMPLETED",
        "expected_decision": "REVIEW",
        "expected_primary_reason_code": "TOXIC_THREAT_INDIRECT",
        "expected_secondary_reason_codes": [],
    },
    {
        "case_id": "B02",
        "topic_id": "07_relevance_usefulness",
        "title": "Очень общий отзыв с низкой информативностью",
        "review": {
            "request_id": "req-b02",
            "review": {
                "review_id": "rvw-b02",
                "text": "Норм",
                "rating": 3,
            },
        },
        "expected_status": "COMPLETED",
        "expected_decision": "REVIEW",
        "expected_primary_reason_code": "REL_LOW_INFORMATION",
        "expected_secondary_reason_codes": [],
    },
    {
        "case_id": "B03",
        "topic_id": "10_legal_reputation",
        "title": "Спорная формулировка с репутационным риском",
        "review": {
            "request_id": "req-b03",
            "review": {
                "review_id": "rvw-b03",
                "text": "Похоже на мошенничество, но доказательств у меня нет",
                "rating": 2,
            },
        },
        "expected_status": "COMPLETED",
        "expected_decision": "REVIEW",
        "expected_primary_reason_code": "LEGAL_REPUTATION_ESCALATION",
        "expected_secondary_reason_codes": [],
    },
]

all_cases = violation_cases + clean_cases + borderline_cases
