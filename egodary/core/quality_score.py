"""Quality score (0–100) from cross-category compatibility rules."""

from __future__ import annotations

from pydantic import BaseModel, Field

from egodary.core.models import PromptState
from egodary.core.rule_matching import iter_cross_bonuses, iter_cross_penalties

BASE_SCORE = 100

LEVEL_THRESHOLDS: tuple[tuple[int, str], ...] = (
    (90, "Отлично"),
    (75, "Хорошо"),
    (60, "Средне"),
    (40, "Плохо"),
    (0, "Очень плохо"),
)

SEVERITY_NORMALIZE: dict[str, str] = {
    "hard_block": "hard",
    "strong_warning": "strong",
    "soft_warning": "weak",
    "medium": "medium",
    "overload": "overload",
    "style_mismatch": "style_mismatch",
}

SEVERITY_DEFAULT_PENALTY: dict[str, int] = {
    "hard": -45,
    "hard_block": -45,
    "strong": -30,
    "strong_warning": -28,
    "medium": -18,
    "weak": -8,
    "soft_warning": -8,
    "overload": -15,
    "style_mismatch": -22,
}

SEVERITY_LABELS_RU: dict[str, str] = {
    "hard": "жёсткий конфликт",
    "strong": "сильный конфликт",
    "medium": "средний конфликт",
    "weak": "слабый конфликт",
    "overload": "перегрузка",
    "style_mismatch": "несоответствие стиля",
}

TIER_DEFAULT_BONUS: dict[str, int] = {
    "good": 8,
    "strong": 12,
    "excellent": 18,
    "hint": 5,
}


class QualityIssue(BaseModel):
    message: str
    severity: str
    severity_label: str
    penalty: int
    recommendation: str | None = None


class QualityBonus(BaseModel):
    message: str
    tier: str
    bonus: int


class QualityScoreResult(BaseModel):
    score: int
    level: str
    issues: list[QualityIssue] = Field(default_factory=list)
    bonuses: list[QualityBonus] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


def _scoring_config() -> dict:
    from egodary.core.rule_matching import load_cross_rules

    return load_cross_rules().get("scoring") or {}


def score_level(score: int) -> str:
    thresholds = _scoring_config().get("level_thresholds") or LEVEL_THRESHOLDS
    parsed: list[tuple[int, str]] = []
    for entry in thresholds:
        if isinstance(entry, (list, tuple)) and len(entry) == 2:
            parsed.append((int(entry[0]), str(entry[1])))
        elif isinstance(entry, dict):
            parsed.append((int(entry.get("min", 0)), str(entry.get("label", ""))))
    if not parsed:
        parsed = list(LEVEL_THRESHOLDS)
    for threshold, label in parsed:
        if score >= threshold:
            return label
    return "Очень плохо"


def _clamp_score(value: int) -> int:
    return max(0, min(100, value))


def _normalize_severity(raw: str) -> str:
    return SEVERITY_NORMALIZE.get(raw, raw)


def _penalty_for_rule(rule: dict) -> int:
    if rule.get("penalty") is not None:
        return int(rule["penalty"])
    severity = rule.get("severity", "strong_warning")
    configured = _scoring_config().get("severity_penalties") or {}
    normalized = _normalize_severity(severity)
    if severity in configured:
        return int(configured[severity])
    if normalized in configured:
        return int(configured[normalized])
    return SEVERITY_DEFAULT_PENALTY.get(severity, SEVERITY_DEFAULT_PENALTY.get(normalized, -15))


def _bonus_for_rule(rule: dict) -> int:
    if rule.get("bonus") is not None:
        return int(rule["bonus"])
    tier = rule.get("tier", "hint")
    configured = _scoring_config().get("tier_bonuses") or {}
    if tier in configured:
        return int(configured[tier])
    return TIER_DEFAULT_BONUS.get(tier, 5)


def compute_quality_score(state: PromptState, registry=None) -> QualityScoreResult:
    """Compute quality score from matched cross-rules penalties and bonuses."""
    del registry  # reserved for future registry-aware rules

    issues: list[QualityIssue] = []
    bonuses: list[QualityBonus] = []
    recommendations: list[str] = []
    penalty_total = 0
    bonus_total = 0

    for rule in iter_cross_penalties(state):
        raw_severity = rule.get("severity", "medium")
        severity = _normalize_severity(raw_severity)
        penalty = _penalty_for_rule(rule)
        penalty_total += penalty
        recommendation = rule.get("recommendation")
        issues.append(
            QualityIssue(
                message=rule.get("message", rule.get("id", "conflict")),
                severity=severity,
                severity_label=SEVERITY_LABELS_RU.get(severity, severity),
                penalty=penalty,
                recommendation=recommendation,
            )
        )
        if recommendation and recommendation not in recommendations:
            recommendations.append(recommendation)

    for rule in iter_cross_bonuses(state):
        tier = rule.get("tier", "hint")
        bonus = _bonus_for_rule(rule)
        bonus_total += bonus
        bonuses.append(
            QualityBonus(
                message=rule.get("message", rule.get("id", "synergy")),
                tier=tier,
                bonus=bonus,
            )
        )

    score = _clamp_score(int(_scoring_config().get("base_score", BASE_SCORE)) + penalty_total + bonus_total)
    return QualityScoreResult(
        score=score,
        level=score_level(score),
        issues=issues,
        bonuses=bonuses,
        recommendations=recommendations,
    )
