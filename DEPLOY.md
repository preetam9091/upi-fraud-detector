# UPI Fraud Detector — Phase 4 Deployment Guide

## Railway Deployment (Free Tier)

### Step 1: Install Railway CLI
```bash
npm install -g @railway/cli
railway login
```

### Step 2: Initialise project
```bash
cd /path/to/upi-fraud-detector
railway init
# Choose: "Empty Project"
```

### Step 3: Set environment variables in Railway dashboard
```
MODEL_PATH=model/artifacts/fraud_model.pkl
FEATURES_PATH=model/artifacts/feature_cols.pkl
SUPABASE_URL=https://xxxx.supabase.co        # optional
SUPABASE_KEY=your_anon_key                    # optional
```

### Step 4: Deploy
```bash
railway up
```

Railway auto-detects the `Procfile` and runs:
```
web: uvicorn api.main:app --host 0.0.0.0 --port $PORT
```

Your live URL will be: `https://your-project.up.railway.app`

---

## Render Deployment (Alternative Free Tier)

1. Push repo to GitHub
2. Go to [render.com](https://render.com) → New Web Service → Connect GitHub repo
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
5. Set env vars in Render dashboard (same as above)

---

## Supabase Setup (Audit Log)

Run this SQL in your Supabase SQL editor to create the audit table:

```sql
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

-- Index for fast queries by user or transaction
create index on scored_transactions (user_id);
create index on scored_transactions (transaction_id);
create index on scored_transactions (scored_at desc);
```

Then add to your `.env`:
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
```
