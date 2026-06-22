# UPI Fraud Detection System

Real-time fraud scoring API for UPI transactions. Send a transaction, get a risk score and explanation back in under 20ms.

Built this because India's UPI ecosystem processes 18 billion transactions a month and there's no affordable, India-native fraud detection API for small fintechs. The enterprise tools (Feedzai, Sardine) cost $50k+/year and aren't built for UPI patterns. This is.

---

## What it does

```bash
curl -X POST https://your-api/v1/score \
  -d '{
    "user_id": "user_42",
    "amount": 49800,
    "device_id": "device_new_unknown",
    "primary_device": "device_registered",
    "timestamp": "2024-11-01T03:14:00",
    "recipient_seen_before": 0,
    "avg_txn_amount": 1200
  }'
```

```json
{
  "risk_score": 0.97,
  "risk_label": "CRITICAL",
  "flags": ["NEW_DEVICE", "ODD_HOUR", "AMOUNT_8X_AVERAGE", "FIRST_TIME_RECIPIENT", "THRESHOLD_GAMING"],
  "shap_top5": [
    {"feature": "amount_zscore",      "shap": +0.41, "direction": "↑ fraud"},
    {"feature": "amount_vs_user_avg", "shap": +0.38, "direction": "↑ fraud"},
    {"feature": "is_new_device",      "shap": +0.12, "direction": "↑ fraud"},
    {"feature": "is_odd_hour",        "shap": +0.09, "direction": "↑ fraud"},
    {"feature": "recipient_seen_before", "shap": +0.07, "direction": "↑ fraud"}
  ],
  "latency_ms": 16.95
}
```

That transaction is a textbook account takeover — ₹49,800 (just below the ₹50k scrutiny threshold), sent at 3am, from a device the user has never used, to someone they've never paid before. The system catches it and tells you exactly why.

---

## How it's built

```
Transactions (CSV / live stream)
    │
    ▼
Go Producer → Kafka (raw-transactions topic)
    │
    ▼
Go Consumer → reads user baseline from Redis
    │           updates baseline after each transaction
    ▼
FastAPI (/v1/score)
    ├── 18 features computed per transaction
    ├── XGBoost model (loaded at startup, <20ms inference)
    ├── SHAP explainability (top 5 drivers per prediction)
    ├── 9 rule-based flags (human-auditable)
    └── PostgreSQL audit log (every prediction stored)
```

**Why these choices:**
- **Go for the pipeline** — goroutines handle 100+ TPS with low memory overhead
- **Kafka** — decouples ingestion from scoring; transactions queue up if the model slows down, nothing is lost
- **Redis for baselines** — per-user rolling mean/variance stored as a hash, updated in O(1) using Welford's algorithm. No transaction history needed.
- **XGBoost over neural nets** — tabular data, interpretable with SHAP, <20ms inference, industry standard for fraud

---

## The 5 fraud patterns it detects

India's UPI fraud has specific fingerprints. These aren't generic — they're based on RBI Annual Report 2024 fraud category breakdowns.

| Pattern | What the attacker does | Signal in data |
|---|---|---|
| Account Takeover | Steals SIM, logs into your UPI app | New device + 3am + amount 5x average + rapid succession |
| Vishing | Calls pretending to be your bank | Large single transfer, new recipient, user's own device |
| Mule Chain | Uses your account to launder stolen money | High fan-in (many senders → you) + immediate forward |
| New Account Fraud | Fake KYC, opens account just to default | Account age < 30 days + large amount immediately |
| Threshold Gaming | Splits ₹1.5L into three ₹49,800 transfers | Multiple transfers just below ₹50k threshold |

---

## The data problem (honest answer)

No public labeled UPI transaction dataset exists. NPCI doesn't release one. No Indian bank does. So I built a simulator that generates realistic transactions calibrated to RBI statistics — 500k transactions, 0.3% fraud rate, matching the RBI's per-transaction fraud definition.

The classification metrics (AUC, precision, recall) are near-perfect because of same-distribution evaluation — the model is tested on data from the same simulator it trained on. That's expected, not a meaningful accuracy claim.

The metrics that are real:
- **Inference latency: <20ms** — measurable, doesn't depend on data
- **Cold start: ~190ms** — measurable, doesn't depend on data
- **Kafka throughput: 100 TPS** — measurable, doesn't depend on data

A fintech partner with real labeled transactions could swap in their data and run the same pipeline. That's the architecture decision — the infrastructure is production-ready, the model just needs real data to be production-meaningful.

---

## Running locally

**Prerequisites:** Python 3.11+, Go 1.22+, Docker

```bash
# Clone
git clone https://github.com/preetam9091/upi-fraud-detector
cd upi-fraud-detector

# Python setup
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Generate training data + train model
python3 generate.py        # ~2 min, generates 500k transactions
python3 train_model.py     # ~5 min, trains XGBoost + saves model

# Start Kafka + Redis
docker compose up -d

# Start the API
uvicorn api.main:app --reload

# Test it
curl http://localhost:8000/health
```

Interactive API docs at `http://localhost:8000/docs`

---

## Endpoints

| Method | Path | What it does |
|---|---|---|
| GET | `/health` | Liveness check + cold start time |
| POST | `/v1/score` | Score a single transaction |
| POST | `/v1/batch` | Score up to 100 transactions at once |
| GET | `/docs` | Swagger UI |

---

## Stack

Python · Go · Apache Kafka · Redis · XGBoost · SHAP · FastAPI · PostgreSQL · Docker · Next.js
