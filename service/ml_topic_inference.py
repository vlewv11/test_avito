from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib


@dataclass
class TopicModelConfig:
    topic_id: str
    artifact_path: Path
    review_threshold: float
    reject_threshold: float
    checksum: str | None


class MLTopicEnsemble:
    def __init__(self, manifest_path: str | Path) -> None:
        self.manifest_path = Path(manifest_path)
        self.model_set_version = "unknown"
        self.models: dict[str, Any] = {}
        self.configs: dict[str, TopicModelConfig] = {}
        self.available_topics: set[str] = set()
        self._load_manifest_and_models()

    def _load_manifest_and_models(self) -> None:
        if not self.manifest_path.exists():
            raise FileNotFoundError(f"Manifest file not found: {self.manifest_path}")

        raw = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        self.model_set_version = str(raw.get("model_set_version", "unknown"))
        topics = raw.get("topics", {})
        if not isinstance(topics, dict):
            raise ValueError(f"Invalid manifest topics format (expected object): {self.manifest_path}")

        for topic_id, cfg in topics.items():
            if not isinstance(cfg, dict):
                raise ValueError(f"Invalid topic config for '{topic_id}': expected object")
            artifact_rel = cfg.get("artifact")
            if not isinstance(artifact_rel, str):
                raise ValueError(f"Invalid or missing artifact for topic '{topic_id}'")

            artifact_path = (self.manifest_path.parent / artifact_rel).resolve()
            topic_cfg = TopicModelConfig(
                topic_id=topic_id,
                artifact_path=artifact_path,
                review_threshold=float(cfg.get("review_threshold", 0.6)),
                reject_threshold=float(cfg.get("reject_threshold", 0.85)),
                checksum=str(cfg["checksum"]) if cfg.get("checksum") else None,
            )
            self.configs[topic_id] = topic_cfg

            if not artifact_path.exists():
                raise FileNotFoundError(f"Model artifact not found for topic '{topic_id}': {artifact_path}")
            if topic_cfg.checksum and not self._checksum_ok(artifact_path, topic_cfg.checksum):
                raise ValueError(f"Checksum mismatch for topic '{topic_id}': {artifact_path}")
            self.models[topic_id] = joblib.load(artifact_path)
            self.available_topics.add(topic_id)

    @staticmethod
    def _checksum_ok(path: Path, expected: str) -> bool:
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        return actual == expected

    @staticmethod
    def _sigmoid(x: float) -> float:
        if x >= 0:
            z = math.exp(-x)
            return 1.0 / (1.0 + z)
        z = math.exp(x)
        return z / (1.0 + z)

    @staticmethod
    def build_text_features(review: dict[str, Any]) -> str:
        text = str(review.get("text", ""))
        rating = review.get("rating")
        rating_token = f" rating_{rating}" if isinstance(rating, int) else ""
        image_tokens = " ".join(
            str(img.get("url", "")).lower() for img in review.get("images", []) if isinstance(img, dict)
        )
        return f"{text}{rating_token} {image_tokens}".strip()

    def score_topics(self, review: dict[str, Any]) -> dict[str, float]:
        features = self.build_text_features(review)
        scores: dict[str, float] = {}

        for topic_id, model in self.models.items():
            score = 0.0
            if hasattr(model, "predict_proba"):
                proba = model.predict_proba([features])[0]
                if len(proba) >= 2:
                    score = float(proba[1])
            elif hasattr(model, "decision_function"):
                margin = float(model.decision_function([features])[0])
                score = self._sigmoid(margin)
            scores[topic_id] = max(0.0, min(1.0, score))

        return scores

    def topic_thresholds(self, topic_id: str) -> tuple[float, float]:
        cfg = self.configs.get(topic_id)
        if not cfg:
            return 0.6, 0.85
        return cfg.review_threshold, cfg.reject_threshold

DEFAULT_MANIFEST_PATH = Path(__file__).resolve().parent / "models" / "manifest.json"


def load_ml_ensemble(manifest_path: str | Path | None = None) -> MLTopicEnsemble:
    return MLTopicEnsemble(manifest_path or DEFAULT_MANIFEST_PATH)
