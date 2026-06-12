"""
Phase 4 — UPI Fraud Detector Scoring API
=========================================

FastAPI application exposing:
  POST /v1/score        — score a single transaction
  POST /v1/batch        — score up to 100 transactions in one call
  GET  /health          — liveness + model status + cold-start time

Design decisions
----------------
* Model loaded once at startup → cached in module-level singletons.
  Never reload on each request — that would add ~500ms latency.

* SHAP TreeExplainer is also built once at startup.
  TreeExplainer is thread-safe for read operations.

* Supabase writes are best-effort (fire-and-forget).
  A DB failure must NEVER break scoring.

* All routes return 200 even for high-risk fraud — the caller decides
  what to do. We return a risk_score + is_fraud bool, not an HTTP error.
"""

from __future__ import annotations

import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Optional

import joblib
import numpy as np
import shap
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from api.audit_log import log_scored_transaction
from api.feature_builder import build_feature_vector, get_flags, get_risk_label
from api.models import (
    BatchRequest, BatchResponse,
    HealthResponse,
    ScoreResponse, SHAPExplanation,
    TransactionRequest,
)

# ─────────────────────────────────────────────────────────────────────────────
load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")
logger = logging.getLogger("fraud_api")

# ── Module-level singletons (loaded once at startup) ──────────────────────────
_model        = None
_explainer    = None
_feature_cols = None
_start_time   = None          # process start (for uptime)
_cold_start_ms: Optional[float] = None   # time to first-ready state


# ─────────────────────────────────────────────────────────────────────────────
# STARTUP / SHUTDOWN
# ─────────────────────────────────────────────────────────────────────────────

MODEL_PATH   = os.getenv("MODEL_PATH",   "model/artifacts/fraud_model.pkl")
FEATURES_PATH = os.getenv("FEATURES_PATH", "model/artifacts/feature_cols.pkl")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load model + SHAP explainer before the first request arrives."""
    global _model, _explainer, _feature_cols, _start_time, _cold_start_ms

    _start_time = time.time()
    logger.info("=== UPI Fraud Detector API — starting up ===")

    t0 = time.perf_counter()

    # Load XGBoost model
    logger.info(f"Loading model from {MODEL_PATH} ...")
    _model = joblib.load(MODEL_PATH)
    logger.info("Model loaded ✓")

    # Load feature column order (must match training)
    _feature_cols = joblib.load(FEATURES_PATH)
    logger.info(f"Feature columns loaded: {_feature_cols} ✓")

    # Build SHAP TreeExplainer (fast for XGBoost, no background data needed)
    logger.info("Building SHAP TreeExplainer ...")
    _explainer = shap.TreeExplainer(_model)
    logger.info("SHAP explainer ready ✓")

    _cold_start_ms = (time.perf_counter() - t0) * 1000
    logger.info(f"Cold start completed in {_cold_start_ms:.1f} ms")
    logger.info("=== API ready — listening for requests ===")

    yield  # ← application runs here

    logger.info("=== Shutting down ===")


# ─────────────────────────────────────────────────────────────────────────────
# APP FACTORY
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="UPI Fraud Detector API",
    description=(
        "Real-time fraud scoring for UPI transactions. "
        "Returns a risk score [0–1], human-readable risk label, "
        "rule-based flags, and SHAP feature explanations."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────────────────────
# CORE SCORING LOGIC
# ─────────────────────────────────────────────────────────────────────────────

def _score_one(req: TransactionRequest) -> ScoreResponse:
    """
    Score a single transaction. Called by both /v1/score and /v1/batch.

    Steps:
    1. Build feature vector (same columns as training)
    2. XGBoost predict_proba → risk score
    3. SHAP TreeExplainer → top-5 feature contributions
    4. Rule-based flags
    5. Async audit log (Supabase)
    6. Return ScoreResponse
    """
    t_start = time.perf_counter()

    # 1. Feature vector
    X = build_feature_vector(req)

    # 2. Model inference
    risk_score = float(_model.predict_proba(X)[0, 1])
    is_fraud   = risk_score >= 0.5
    risk_label = get_risk_label(risk_score)

    # 3. SHAP values (per-feature additive contributions)
    shap_vals   = _explainer.shap_values(X)[0]   # shape: (n_features,)
    feature_names = list(X.columns)
    feature_vals  = X.iloc[0].tolist()

    top_indices = np.argsort(np.abs(shap_vals))[-5:][::-1]
    shap_top5 = [
        SHAPExplanation(
            feature   = feature_names[i],
            value     = round(float(feature_vals[i]), 4),
            shap_contribution = round(float(shap_vals[i]), 4),
            direction = "↑ toward fraud" if shap_vals[i] > 0 else "↓ away from fraud",
        )
        for i in top_indices
    ]

    # 4. Rule flags
    flags = get_flags(req, {})

    latency_ms = (time.perf_counter() - t_start) * 1000

    # 5. Audit log (non-blocking — errors are caught inside)
    log_scored_transaction(
        transaction_id = req.transaction_id,
        user_id        = req.user_id,
        recipient_vpa  = req.recipient_vpa,
        amount         = req.amount,
        timestamp      = req.timestamp,
        risk_score     = risk_score,
        risk_label     = risk_label,
        is_fraud       = is_fraud,
        flags          = flags,
        shap_top5      = [s.model_dump() for s in shap_top5],
        latency_ms     = latency_ms,
    )

    return ScoreResponse(
        transaction_id = req.transaction_id,
        risk_score     = round(risk_score, 4),
        risk_label     = risk_label,
        is_fraud       = is_fraud,
        flags          = flags,
        shap_top5      = shap_top5,
        latency_ms     = round(latency_ms, 2),
    )


# ─────────────────────────────────────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse, tags=["Ops"])
def health():
    """
    Liveness + readiness check.

    Returns model load status and cold-start time (useful for Railway/Render
    where cold-start latency is a key operational metric).
    """
    if _model is None:
        raise HTTPException(status_code=503, detail="Model not loaded yet")

    return HealthResponse(
        status         = "ok",
        model_loaded   = True,
        model_path     = MODEL_PATH,
        feature_count  = len(_feature_cols),
        uptime_seconds = round(time.time() - _start_time, 1) if _start_time else 0,
        cold_start_ms  = round(_cold_start_ms, 1) if _cold_start_ms else None,
    )


@app.post("/v1/score", response_model=ScoreResponse, tags=["Scoring"])
def score_transaction(req: TransactionRequest):
    """
    Score a single UPI transaction.

    Returns:
    - **risk_score**: fraud probability in [0.0, 1.0]
    - **risk_label**: LOW / MEDIUM / HIGH / CRITICAL
    - **is_fraud**: True if risk_score >= 0.5
    - **flags**: list of rule-based red flags triggered
    - **shap_top5**: top-5 SHAP feature contributions explaining the score
    - **latency_ms**: end-to-end inference time

    Every scored transaction is also written to Supabase for audit purposes
    (if SUPABASE_URL + SUPABASE_KEY env vars are set).
    """
    if _model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    return _score_one(req)


@app.post("/v1/batch", response_model=BatchResponse, tags=["Scoring"])
def score_batch(req: BatchRequest):
    """
    Score up to 100 transactions in a single HTTP call.

    Useful for:
    - Bulk re-scoring of historical transactions
    - Integration tests
    - Load testing without HTTP overhead per transaction

    Each transaction is scored independently. Results preserve input order.
    """
    if _model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    t_batch_start = time.perf_counter()
    results = [_score_one(txn) for txn in req.transactions]
    batch_latency_ms = (time.perf_counter() - t_batch_start) * 1000

    fraud_count = sum(1 for r in results if r.is_fraud)

    return BatchResponse(
        results          = results,
        total            = len(results),
        fraud_count      = fraud_count,
        batch_latency_ms = round(batch_latency_ms, 2),
    )
