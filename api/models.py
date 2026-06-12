"""
Pydantic schemas for Phase 4 Scoring API.

Design principle: the caller sends raw transaction fields (same columns
that the PaySim simulator produces), and the API returns a fully-enriched
response — risk score, binary verdict, triggered rule flags, and SHAP-based
feature explanations so a human can understand *why* the model flagged it.
"""

from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field


# ─────────────────────────────────────────────
# REQUEST SCHEMAS
# ─────────────────────────────────────────────

class TransactionRequest(BaseModel):
    """
    A single UPI transaction to score.

    All monetary fields are in Indian Rupees (₹).
    Timestamps are ISO-8601 strings (e.g. "2025-01-15T23:45:00").
    """
    transaction_id: str = Field(..., description="Unique transaction identifier")
    user_id: str = Field(..., description="Sender's UPI user ID")
    recipient_vpa: str = Field(..., description="Recipient's Virtual Payment Address")
    amount: float = Field(..., gt=0, description="Transaction amount in ₹")
    timestamp: str = Field(..., description="ISO-8601 timestamp of transaction")
    device_id: str = Field(..., description="Device fingerprint / identifier")

    # Pre-computed behavioral context (cached in Redis in production)
    avg_txn_amount: float = Field(500.0, description="User's historical average transaction amount")
    account_age_days: int = Field(365, description="Days since account was created")
    user_txn_rank: int = Field(0, description="Number of previous transactions by this user")
    days_since_last_txn: float = Field(1.0, description="Days since user's last transaction")
    rolling_mean: float = Field(500.0, description="Rolling mean of last 30 txns")
    rolling_std: float = Field(150.0, description="Rolling std of last 30 txns")
    primary_device: str = Field("device_0", description="User's registered primary device")
    city_tier: str = Field("tier1", description="User's city tier (tier1/tier2/tier3)")
    recipient_fan_in: int = Field(1, description="# unique senders this recipient has received from")
    sender_fan_out: int = Field(1, description="# unique recipients this sender has sent to")
    recipient_seen_before: int = Field(1, description="1 if sender has paid this recipient before")
    is_festival_day: int = Field(0, description="1 if today is an Indian festival/holiday")

    model_config = {
        "json_schema_extra": {
            "example": {
                "transaction_id": "TXN-DEMO-001",
                "user_id": "user_42",
                "recipient_vpa": "fraud04fb50@ybl",
                "amount": 24285,
                "timestamp": "2025-03-10T19:00:00",
                "device_id": "device_brand_new",
                "avg_txn_amount": 1080,
                "account_age_days": 12,
                "user_txn_rank": 42,
                "days_since_last_txn": 4.1,
                "rolling_mean": 1050,
                "rolling_std": 120,
                "primary_device": "device_registered_old",
                "city_tier": "tier1",
                "recipient_fan_in": 1,
                "sender_fan_out": 20,
                "recipient_seen_before": 0,
                "is_festival_day": 0,
            }
        }
    }


class BatchRequest(BaseModel):
    """Up to 100 transactions scored in a single HTTP call."""
    transactions: list[TransactionRequest] = Field(
        ..., min_length=1, max_length=100,
        description="List of transactions to score (max 100)"
    )


# ─────────────────────────────────────────────
# RESPONSE SCHEMAS
# ─────────────────────────────────────────────

class SHAPExplanation(BaseModel):
    """Top-N SHAP feature contributions for a single prediction."""
    feature: str
    value: float
    shap_contribution: float
    direction: str   # "↑ toward fraud" or "↓ away from fraud"


class ScoreResponse(BaseModel):
    """Full scoring response for one transaction."""
    transaction_id: str
    risk_score: float = Field(..., description="Fraud probability [0.0 – 1.0]")
    risk_label: str = Field(..., description="LOW / MEDIUM / HIGH / CRITICAL")
    is_fraud: bool = Field(..., description="True if risk_score >= 0.5")

    # Rule-based flags that triggered (human-readable)
    flags: list[str] = Field(default_factory=list)

    # Top-5 SHAP explanations
    shap_top5: list[SHAPExplanation] = Field(default_factory=list)

    # Latency
    latency_ms: float

    class Config:
        json_schema_extra = {
            "example": {
                "transaction_id": "TXN-DEMO-001",
                "risk_score": 0.932,
                "risk_label": "CRITICAL",
                "is_fraud": True,
                "flags": [
                    "HIGH_AMOUNT_VS_HISTORY",
                    "ODD_HOUR_TRANSACTION",
                    "NEW_DEVICE",
                    "AMOUNT_NEAR_50K_THRESHOLD",
                ],
                "shap_top5": [
                    {"feature": "amount_zscore", "value": 8.2,
                     "shap_contribution": 0.41, "direction": "↑ toward fraud"},
                ],
                "latency_ms": 12.4,
            }
        }


class BatchResponse(BaseModel):
    """Batch scoring response."""
    results: list[ScoreResponse]
    total: int
    fraud_count: int
    batch_latency_ms: float


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    model_loaded: bool
    model_path: str
    feature_count: int
    uptime_seconds: float
    cold_start_ms: Optional[float] = None
