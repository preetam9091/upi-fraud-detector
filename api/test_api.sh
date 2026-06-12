#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Phase 4 — API smoke test + latency benchmark
# Usage: bash api/test_api.sh
# ─────────────────────────────────────────────────────────────────────────────

BASE_URL="${API_URL:-http://localhost:8000}"
PASS=0
FAIL=0
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

ok()   { echo -e "${GREEN}  ✓ $1${NC}"; ((PASS++)); }
fail() { echo -e "${RED}  ✗ $1${NC}"; ((FAIL++)); }
info() { echo -e "${YELLOW}  → $1${NC}"; }

echo "═══════════════════════════════════════════════════"
echo "  UPI Fraud Detector — Phase 4 API Test Suite"
echo "  Base URL: ${BASE_URL}"
echo "═══════════════════════════════════════════════════"

# ── 1. Health check ───────────────────────────────────────────────────────────
echo ""
echo "▶ 1/4  Health check"
HEALTH=$(curl -sf "${BASE_URL}/health")
if [ $? -eq 0 ]; then
    ok "GET /health  → 200"
    MODEL_LOADED=$(echo "$HEALTH" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['model_loaded'])")
    COLD=$(echo "$HEALTH"        | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('cold_start_ms','?'))")
    ok "model_loaded = ${MODEL_LOADED}"
    info "Cold start: ${COLD} ms"
else
    fail "GET /health failed"
fi

# ── 2. Score a clear-fraud transaction ────────────────────────────────────────
echo ""
echo "▶ 2/4  Score: high-risk fraud transaction"
FRAUD_PAYLOAD='{
  "transaction_id": "TXN-TEST-FRAUD-001",
  "user_id": "user_suspect_42",
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
}'

FRAUD_RESP=$(curl -sf -X POST "${BASE_URL}/v1/score" \
  -H "Content-Type: application/json" \
  -d "${FRAUD_PAYLOAD}")

if [ $? -eq 0 ]; then
    ok "POST /v1/score  → 200"
    SCORE=$(echo "$FRAUD_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['risk_score'])")
    LABEL=$(echo "$FRAUD_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['risk_label'])")
    IS_FRAUD=$(echo "$FRAUD_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['is_fraud'])")
    LATENCY=$(echo "$FRAUD_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['latency_ms'])")
    FLAGS=$(echo "$FRAUD_RESP"   | python3 -c "import sys,json; d=json.load(sys.stdin); print(', '.join(d['flags']))")
    info "  risk_score = ${SCORE}  |  label = ${LABEL}  |  is_fraud = ${IS_FRAUD}"
    info "  latency    = ${LATENCY} ms"
    info "  flags      = ${FLAGS}"
    if [ "$IS_FRAUD" = "True" ]; then
        ok "Correctly identified as fraud"
    else
        fail "Expected is_fraud=True, got ${IS_FRAUD}"
    fi
else
    fail "POST /v1/score failed for fraud transaction"
fi

# ── 3. Score a clear-legit transaction ────────────────────────────────────────
echo ""
echo "▶ 3/4  Score: low-risk legitimate transaction"
LEGIT_PAYLOAD='{
  "transaction_id": "TXN-TEST-LEGIT-001",
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
}'

LEGIT_RESP=$(curl -sf -X POST "${BASE_URL}/v1/score" \
  -H "Content-Type: application/json" \
  -d "${LEGIT_PAYLOAD}")

if [ $? -eq 0 ]; then
    ok "POST /v1/score  → 200"
    SCORE=$(echo "$LEGIT_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['risk_score'])")
    LABEL=$(echo "$LEGIT_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['risk_label'])")
    IS_FRAUD=$(echo "$LEGIT_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['is_fraud'])")
    info "  risk_score = ${SCORE}  |  label = ${LABEL}  |  is_fraud = ${IS_FRAUD}"
    if [ "$IS_FRAUD" = "False" ]; then
        ok "Correctly identified as legit"
    else
        fail "Expected is_fraud=False, got ${IS_FRAUD}"
    fi
else
    fail "POST /v1/score failed for legit transaction"
fi

# ── 4. Batch endpoint ─────────────────────────────────────────────────────────
echo ""
echo "▶ 4/4  Batch endpoint (2 transactions)"
BATCH_PAYLOAD="{\"transactions\": [${FRAUD_PAYLOAD}, ${LEGIT_PAYLOAD}]}"

BATCH_RESP=$(curl -sf -X POST "${BASE_URL}/v1/batch" \
  -H "Content-Type: application/json" \
  -d "${BATCH_PAYLOAD}")

if [ $? -eq 0 ]; then
    ok "POST /v1/batch  → 200"
    TOTAL=$(echo "$BATCH_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['total'])")
    FRAUD_COUNT=$(echo "$BATCH_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['fraud_count'])")
    BATCH_LAT=$(echo "$BATCH_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['batch_latency_ms'])")
    info "  total=${TOTAL}  fraud_count=${FRAUD_COUNT}  batch_latency=${BATCH_LAT} ms"
    if [ "$TOTAL" = "2" ] && [ "$FRAUD_COUNT" = "1" ]; then
        ok "Batch results correct (1/2 fraud)"
    else
        fail "Unexpected batch results: total=${TOTAL} fraud_count=${FRAUD_COUNT}"
    fi
else
    fail "POST /v1/batch failed"
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════"
echo -e "  Tests passed: ${GREEN}${PASS}${NC}   Tests failed: ${RED}${FAIL}${NC}"
echo "═══════════════════════════════════════════════════"
[ "$FAIL" -eq 0 ] && exit 0 || exit 1
