"""
Feature engineering for *serving* (single transaction at inference time).

In training  → we compute rolling stats across all historical rows.
In serving   → the caller provides pre-computed context (rolling_mean, rolling_std,
               days_since_last_txn, etc.) which in production would come from Redis.

This module converts one TransactionRequest into the exact same feature vector
that the XGBoost model was trained on.
"""

from __future__ import annotations
import numpy as np
import pandas as pd
from datetime import datetime

from api.models import TransactionRequest


# Feature order must match what was used during training (model/artifacts/feature_cols.pkl)
FEATURE_COLS = [
    # Time
    "hour", "day_of_week", "is_odd_hour", "is_weekend",
    # Amount
    "amount_log", "is_round_number", "amount_just_below_50k",
    "amount_vs_user_avg", "amount_zscore",
    # Behavioral
    "account_age_days", "user_txn_rank", "days_since_last_txn",
    "is_new_device", "city_tier_encoded",
    # Phase 1 flags
    "recipient_seen_before", "is_festival_day",
    # Network
    "recipient_fan_in", "sender_fan_out",
]

TIER_MAP = {"tier1": 0, "tier2": 1, "tier3": 2}


def build_feature_vector(req: TransactionRequest) -> pd.DataFrame:
    """
    Convert a single TransactionRequest into a one-row DataFrame of model features.

    Returns a DataFrame (not a dict or array) so that SHAP gets named columns
    for readable explanations.
    """
    ts = datetime.fromisoformat(req.timestamp)
    hour        = ts.hour
    day_of_week = ts.weekday()   # 0=Monday, 6=Sunday

    # ── TIME ──────────────────────────────────────────────────────────────
    is_odd_hour = int(0 <= hour <= 5)
    is_weekend  = int(day_of_week in (5, 6))

    # ── AMOUNT ────────────────────────────────────────────────────────────
    amount_log           = float(np.log1p(req.amount))
    is_round_number      = int(req.amount % 100 == 0)
    amount_just_below_50k = int(45000 <= req.amount <= 49999)
    amount_vs_user_avg   = req.amount / (req.avg_txn_amount + 1e-8)

    rolling_std_safe = req.rolling_std if req.rolling_std > 0 else (req.avg_txn_amount * 0.3 + 1e-8)
    amount_zscore = float(
        np.clip((req.amount - req.rolling_mean) / (rolling_std_safe + 1e-8), -10, 10)
    )

    # ── BEHAVIOURAL ───────────────────────────────────────────────────────
    is_new_device     = int(req.device_id != req.primary_device)
    city_tier_encoded = float(TIER_MAP.get(req.city_tier, 1))

    row = {
        "hour":                   float(hour),
        "day_of_week":            float(day_of_week),
        "is_odd_hour":            float(is_odd_hour),
        "is_weekend":             float(is_weekend),
        "amount_log":             amount_log,
        "is_round_number":        float(is_round_number),
        "amount_just_below_50k":  float(amount_just_below_50k),
        "amount_vs_user_avg":     float(amount_vs_user_avg),
        "amount_zscore":          amount_zscore,
        "account_age_days":       float(req.account_age_days),
        "user_txn_rank":          float(req.user_txn_rank),
        "days_since_last_txn":    float(req.days_since_last_txn),
        "is_new_device":          float(is_new_device),
        "city_tier_encoded":      city_tier_encoded,
        "recipient_seen_before":  float(req.recipient_seen_before),
        "is_festival_day":        float(req.is_festival_day),
        "recipient_fan_in":       float(req.recipient_fan_in),
        "sender_fan_out":         float(req.sender_fan_out),
    }

    return pd.DataFrame([row], columns=FEATURE_COLS)


def get_risk_label(score: float) -> str:
    """Convert a probability score into a human-readable risk tier."""
    if score >= 0.80:
        return "CRITICAL"
    elif score >= 0.50:
        return "HIGH"
    elif score >= 0.25:
        return "MEDIUM"
    else:
        return "LOW"


def get_flags(req: TransactionRequest, features: dict) -> list[str]:
    """
    Rule-based flags — independent of the ML model.
    These are explicit, auditable heuristics that complement the model score.
    In production these would feed into a case management system.
    """
    flags = []

    ts = datetime.fromisoformat(req.timestamp)
    hour = ts.hour

    if 0 <= hour <= 5:
        flags.append("ODD_HOUR_TRANSACTION")

    if req.amount > 5 * req.avg_txn_amount:
        flags.append("HIGH_AMOUNT_VS_HISTORY")

    if 45000 <= req.amount <= 49999:
        flags.append("AMOUNT_NEAR_50K_THRESHOLD")

    if req.device_id != req.primary_device:
        flags.append("NEW_DEVICE")

    if req.account_age_days < 30:
        flags.append("NEW_ACCOUNT")

    if req.recipient_fan_in > 50:
        flags.append("HIGH_FAN_IN_RECIPIENT")   # possible mule account

    if req.sender_fan_out > 10:
        flags.append("HIGH_SENDER_FAN_OUT")

    if req.recipient_seen_before == 0:
        flags.append("FIRST_TIME_RECIPIENT")

    if req.days_since_last_txn > 30:
        flags.append("DORMANT_ACCOUNT_SUDDEN_TXN")

    return flags
