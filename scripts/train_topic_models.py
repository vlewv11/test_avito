#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import classification_report
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import train_test_split
from sklearn.svm import LinearSVC

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

ROOT = Path(__file__).resolve().parent.parent
DATASET = ROOT / "datasets" / "bootstrap_labeled_reviews.jsonl"
MANIFEST = ROOT / "service" / "models" / "manifest.json"
MODELS_DIR = ROOT / "service" / "models"


def build_features(row: dict) -> str:
    text = str(row.get("text", ""))
    rating = row.get("rating")
    rating_token = f" rating_{rating}" if isinstance(rating, int) else ""
    image_tokens = " ".join(str(img.get("url", "")).lower() for img in row.get("images", []) if isinstance(img, dict))
    return f"{text}{rating_token} {image_tokens}".strip()


def load_rows() -> list[dict]:
    rows: list[dict] = []
    with DATASET.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    rows = load_rows()
    if not rows:
        raise SystemExit("dataset is empty")

    features = [build_features(row) for row in rows]

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    topics_cfg = manifest.get("topics", {})

    for topic_id in TOPICS:
        labels = [1 if row.get("topic_id") == topic_id and row.get("expected_decision") in {"REJECT", "REVIEW"} else 0 for row in rows]
        if len(set(labels)) < 2:
            continue

        x_train, x_valid, y_train, y_valid = train_test_split(
            features,
            labels,
            test_size=0.2,
            random_state=42,
            stratify=labels,
        )

        model = make_pipeline(
            TfidfVectorizer(ngram_range=(1, 2), min_df=1, max_features=5000),
            LinearSVC(),
        )
        model.fit(x_train, y_train)

        valid_pred = model.predict(x_valid)
        report = classification_report(y_valid, valid_pred, output_dict=True, zero_division=0)
        pos = report.get("1", {})
        precision = float(pos.get("precision", 0.0))
        recall = float(pos.get("recall", 0.0))
        f1 = float(pos.get("f1-score", 0.0))
        positives = int(sum(labels))
        total = int(len(labels))
        print(
            f"{topic_id}: positives={positives}/{total}, precision={precision:.3f}, recall={recall:.3f}, f1={f1:.3f}"
        )

        artifact_rel = topics_cfg.get(topic_id, {}).get("artifact", f"{topic_id}.joblib")
        artifact_path = MODELS_DIR / artifact_rel
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(model, artifact_path)

        if topic_id in topics_cfg:
            topics_cfg[topic_id]["checksum"] = sha256(artifact_path)

    manifest["topics"] = topics_cfg
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"trained {len(TOPICS)} topic models; manifest updated: {MANIFEST}")


if __name__ == "__main__":
    main()
