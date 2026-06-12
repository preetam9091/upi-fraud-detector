"""
Supabase audit log writer for Phase 4.

Every scored transaction is persisted to Supabase so you have a full audit trail.
This fulfils two purposes:
  1. Production compliance — every fraud decision must be logged with its reasoning.
  2. Resume talking point — "full audit trail in PostgreSQL" on the phase description.

Schema (create once in Supabase SQL editor):

    create table if not exists scored_transactions (
        id              bigserial primary key,
        transaction_id  text        not null,
        user_id         text        not null,
        recipient_vpa   text        not null,
        amount          numeric     not null,
        timestamp       timestamptz not null,
        risk_score      numeric     not null,
        risk_label      text        not null,
        is_fraud        boolean     not null,
        flags           text[]      not null default '{}',
        shap_top5       jsonb       not null default '[]',
        latency_ms      numeric,
        scored_at       timestamptz not null default now()
    );

If SUPABASE_URL / SUPABASE_KEY are not set, the module silently no-ops so the
API still works in local-only mode.
"""

from __future__ import annotations
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

_client = None   # lazy-init; None means Supabase not configured


def _get_client():
    global _client
    if _client is not None:
        return _client

    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_KEY", "")
    if not url or not key:
        return None    # silently skip — local mode

    try:
        from supabase import create_client
        _client = create_client(url, key)
        logger.info("Supabase client initialised — audit logging enabled.")
    except Exception as exc:
        logger.warning(f"Could not create Supabase client: {exc}")
        _client = None

    return _client


def log_scored_transaction(
    *,
    transaction_id: str,
    user_id: str,
    recipient_vpa: str,
    amount: float,
    timestamp: str,
    risk_score: float,
    risk_label: str,
    is_fraud: bool,
    flags: list[str],
    shap_top5: list[dict],
    latency_ms: float,
) -> None:
    """
    Fire-and-forget insert into the scored_transactions table.
    Errors are logged but never raised — we must NOT let DB failures break scoring.
    """
    client = _get_client()
    if client is None:
        return    # Supabase not configured — skip silently

    record = {
        "transaction_id": transaction_id,
        "user_id":        user_id,
        "recipient_vpa":  recipient_vpa,
        "amount":         amount,
        "timestamp":      timestamp,
        "risk_score":     round(risk_score, 6),
        "risk_label":     risk_label,
        "is_fraud":       is_fraud,
        "flags":          flags,
        "shap_top5":      shap_top5,
        "latency_ms":     round(latency_ms, 3),
    }

    try:
        client.table("scored_transactions").insert(record).execute()
    except Exception as exc:
        logger.error(f"Supabase audit log failed for {transaction_id}: {exc}")
