#!/usr/bin/env python3
from __future__ import annotations

import json
import random
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "datasets" / "bootstrap_labeled_reviews.jsonl"
SEED = 42

TOPICS = [
    "01_toxicity_threats",
    "02_pii",
    "03_spam_ads",
    "04_fraud_manipulation",
    "05_adult_shocking",
    "06_illegal_content",
    "07_relevance_usefulness",
    "08_multimodal_consistency",
    "09_evasion_anomalies",
    "10_legal_reputation",
]


def build_samples() -> list[dict]:
    rng = random.Random(SEED)
    rows: list[dict] = []
    idx = 1

    topic_specs = {
        "01_toxicity_threats": {
            "reject": ["Я тебя найду и сломаю руки", "Тебе конец, убью при встрече", "ты мразь, тебя надо избить"],
            "review": ["Тебя найдут, лучше молчи", "цитата: 'ты урод'", "оскорбления в комментариях, проверьте"],
        },
        "02_pii": {
            "reject": ["звоните +7 999 123 45 67", "пишите на test@mail.ru", "карта 4276123412341234 для оплаты"],
            "review": ["мой номер +7 9** *** ** **", "пишите в тг, контакт дам позже", "часть номера карты ****1234"],
        },
        "03_spam_ads": {
            "reject": ["переходите по ссылке, промокод SALE10", "invite code ABCD, подписывайтесь", "реф ссылка дает бонус"],
            "review": ["кажется можно дешевле найти", "есть акция в другом магазине", "возможно скидка по купону"],
        },
        "04_fraud_manipulation": {
            "reject": ["лучший сервис всем советую, идеал", "идеально! лучший сервис, 5 звезд всем", "шаблонный отзыв: топ топ топ"],
            "review": ["новый аккаунт оставил много похожих отзывов", "похоже на накрутку, но не уверен", "подозрительно однотипно"],
        },
        "05_adult_shocking": {
            "reject": ["порно контент в отзыве", "эротика и интим услуги", "шлюхи москвы"],
            "review": ["сомнительное изображение, возможно 18+", "медицинское фото после операции", "неприятное, но не ясно шок ли это"],
        },
        "06_illegal_content": {
            "reject": ["вот шаги как обойти блокировку", "продам наркотики без проверок", "как взломать аккаунт инструкция"],
            "review": ["в новостях говорили про незаконную схему", "кажется это нарушение закона", "сомнительный призыв, проверьте"],
        },
        "07_relevance_usefulness": {
            "reject": ["asdf qwe 123 !!!", "политика выборы митинг", "бессмысленный набор символов"],
            "review": ["норм", "ok", "так себе"],
        },
        "08_multimodal_consistency": {
            "reject": ["ужасный сервис, ничего не работает", "все плохо, но ставлю 5", "товар сломан, 5 звезд"],
            "review": ["возможно сарказм в отзыве", "позитивный текст и 1 звезда", "непонятное противоречие текста и оценки"],
        },
        "09_evasion_anomalies": {
            "reject": ["переходи hxxp://bad[.]site", "пр0д@м доступ, пиши", "обход фuльтра через hxxp"],
            "review": ["т е к с т с пробелами", "😀😀😀😀😀😀😀😀", "строка похожа на кодировку"],
        },
        "10_legal_reputation": {
            "reject": ["эта компания совершает преступления, это факт", "все по национальности такие", "прямая дискриминация группы людей"],
            "review": ["похоже на мошенничество, но без доказательств", "спорное обвинение, нужна проверка", "репутационный риск, не уверен"],
        },
    }

    # 200 per topic: 120 reject + 80 review = 2000 total
    for topic_id in TOPICS:
        spec = topic_specs[topic_id]
        for _ in range(120):
            text = rng.choice(spec["reject"])
            rows.append(
                {
                    "case_id": f"{topic_id}-R-{idx}",
                    "topic_id": topic_id,
                    "expected_decision": "REJECT",
                    "expected_primary_reason_code": None,
                    "text": text,
                    "rating": rng.randint(1, 5),
                    "images": [],
                }
            )
            idx += 1

        for _ in range(80):
            text = rng.choice(spec["review"])
            rows.append(
                {
                    "case_id": f"{topic_id}-V-{idx}",
                    "topic_id": topic_id,
                    "expected_decision": "REVIEW",
                    "expected_primary_reason_code": None,
                    "text": text,
                    "rating": rng.randint(1, 5),
                    "images": [],
                }
            )
            idx += 1

    # 1000 clean/approve
    clean_templates = [
        "доставили быстро, товар работает как ожидалось",
        "поддержка помогла, в целом доволен покупкой",
        "упаковка целая, описание соответствует",
        "обычный отзыв без нарушений и рекламы",
        "товар хороший, цена приемлемая",
    ]
    for _ in range(1000):
        rows.append(
            {
                "case_id": f"CLEAN-{idx}",
                "topic_id": "clean",
                "expected_decision": "APPROVE",
                "expected_primary_reason_code": None,
                "text": rng.choice(clean_templates),
                "rating": rng.randint(3, 5),
                "images": [],
            }
        )
        idx += 1

    rng.shuffle(rows)
    return rows


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    rows = build_samples()
    with OUTPUT.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"dataset rows={len(rows)} written to {OUTPUT}")


if __name__ == "__main__":
    main()
