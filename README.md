# UPI Fraud Detector

> **Deployed fraud scoring REST API on Railway; sub-200ms p99 latency, SHAP-based explanations on every prediction, full audit trail in PostgreSQL**

A production-grade UPI transaction fraud detection system built across 4 phases:

| Phase | What was built | Stack |
|-------|---------------|-------|
| 1 | RBI-calibrated synthetic UPI transactions (400K transactions, 0.3% fraud) | Python |
| 2 | XGBoost model with SMOTE, 18 features, AUC-ROC >0.99 | XGBoost, SHAP, scikit-learn |
| 3 | Real-time Kafka streaming pipeline | Go, Kafka, Redis |
| **4** | **Live REST API — score any transaction in <200ms** | **FastAPI, Pydantic, Supabase** |

---

## 🚀 API — Test in 30 seconds

```bash
# 1. Start the API locally
source venv/bin/activate
uvicorn api.main:app --reload

# 2. Health check
curl http://localhost:8000/health | python3 -m json.tool

# 3. Score a fraudulent transaction
curl -X POST http://localhost:8000/v1/score \
  -H "Content-Type: application/json" \
  -d '{
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
    "is_festival_day": 0
  }' | python3 -m json.tool

# 4. Score a legit transaction
curl -X POST http://localhost:8000/v1/score \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_id": "TXN-LEGIT-001",
    "user_id": "user_regular_99",
    "recipient_vpa": "regular_merchant@upi",
    "amount": 350,
    "timestamp": "2025-03-10T11:30:00",
    "device_id": "my_regular_phone",
    "avg_txn_amount": 400,
    "account_age_days": 720,
    "user_txn_rank": 350,
    "days_since_last_txn": 2.0,
    "rolling_mean": 380,
    "rolling_std": 80,
    "primary_device": "my_regular_phone",
    "city_tier": "tier1",
    "recipient_fan_in": 3,
    "sender_fan_out": 2,
    "recipient_seen_before": 1,
    "is_festival_day": 0
  }' | python3 -m json.tool

# 5. Batch score (up to 100 transactions)
curl -X POST http://localhost:8000/v1/batch \
  -H "Content-Type: application/json" \
  -d '{"transactions": [/* array of TransactionRequest */]}' | python3 -m json.tool
```

### Example Response

```json
{
  "transaction_id": "TXN-DEMO-001",
  "risk_score": 1.0,
  "risk_label": "CRITICAL",
  "is_fraud": true,
  "flags": [
    "HIGH_AMOUNT_VS_HISTORY",
    "NEW_DEVICE",
    "NEW_ACCOUNT",
    "HIGH_SENDER_FAN_OUT",
    "FIRST_TIME_RECIPIENT"
  ],
  "shap_top5": [
    {"feature": "amount_zscore",      "value": 10.0, "shap_contribution":  0.41, "direction": "↑ toward fraud"},
    {"feature": "amount_vs_user_avg", "value": 22.5, "shap_contribution":  0.38, "direction": "↑ toward fraud"},
    {"feature": "sender_fan_out",     "value": 20.0, "shap_contribution":  0.12, "direction": "↑ toward fraud"},
    {"feature": "account_age_days",   "value": 12.0, "shap_contribution":  0.09, "direction": "↑ toward fraud"},
    {"feature": "is_new_device",      "value":  1.0, "shap_contribution":  0.07, "direction": "↑ toward fraud"}
  ],
  "latency_ms": 16.95
}
```

---

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET`  | `/health` | Liveness check + cold-start time |
| `POST` | `/v1/score` | Score a single transaction |
| `POST` | `/v1/batch` | Score up to 100 transactions |
| `GET`  | `/docs` | Interactive Swagger UI |
| `GET`  | `/redoc` | ReDoc API reference |

### Risk Labels

| Label | Risk Score | Action |
|-------|-----------|--------|
| `LOW` | 0.00 – 0.25 | Allow |
| `MEDIUM` | 0.25 – 0.50 | Flag for review |
| `HIGH` | 0.50 – 0.80 | Require 2FA |
| `CRITICAL` | 0.80 – 1.00 | Block + alert |

---

## Architecture

```
Client
  │
  ▼
FastAPI  (/v1/score, /v1/batch, /health)
  │
  ├── feature_builder.py   ← compute 18 features from raw transaction
  ├── XGBoost model        ← loaded at startup, cached in memory
  ├── SHAP TreeExplainer   ← top-5 feature explanations per prediction
  ├── rule_flags           ← 9 auditable business rules
  └── Supabase audit log   ← every scored transaction persisted to PostgreSQL
```

---

## Running Locally

```bash
# 1. Clone and set up venv
git clone <repo>
cd upi-fraud-detector
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Generate data + train model (if not already done)
python generate.py
python train_model.py

# 3. Start API
uvicorn api.main:app --reload

# 4. Run smoke tests
bash api/test_api.sh
```

---

## Deployment

See [DEPLOY.md](DEPLOY.md) for Railway and Render deployment instructions.

---

## Model Performance

Trained on 400,000 synthetic UPI transactions (0.375% fraud rate):

| Metric | Score |
|--------|-------|
| AUC-ROC | >0.99 |
| AUC-PR | >0.95 |
| Recall (fraud) | ~99% |
| Precision (fraud) | ~99% |
| Inference latency | <20ms |
| Cold start | ~190ms |

Features: `amount_zscore`, `amount_vs_user_avg`, `sender_fan_out`, `account_age_days`, `is_new_device`, `recipient_seen_before`, and 12 more.
