#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
# Phase 3 Benchmark — Run producer + consumer end-to-end
# ──────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

TPS="${1:-1000}"
LIMIT="${2:-10000}"

echo "══════════════════════════════════════════════════"
echo "  Phase 3 Benchmark"
echo "  TPS: $TPS | Limit: $LIMIT"
echo "══════════════════════════════════════════════════"
echo

# ── Pre-checks ────────────────────────────────────────────────
echo "[1/5] Checking Docker services..."
if ! docker ps | grep -q kafka; then
    echo "  ✗ Kafka not running. Start with: docker compose up -d"
    exit 1
fi
if ! docker ps | grep -q redis; then
    echo "  ✗ Redis not running. Start with: docker compose up -d"
    exit 1
fi
echo "  ✓ Kafka + Redis running"

# ── Build ─────────────────────────────────────────────────────
echo "[2/5] Building Go binaries..."
go build -o producer-bin ./producer/
go build -o consumer-bin ./consumer/
echo "  ✓ Built producer-bin and consumer-bin"

# ── Flush old consumer offsets (optional fresh start) ─────────
echo "[3/5] Flushing Redis user baselines..."
docker exec upi-fraud-detector-redis-1 redis-cli FLUSHDB > /dev/null 2>&1 || true
echo "  ✓ Redis flushed"

# ── Start consumer in background ──────────────────────────────
echo "[4/5] Starting consumer..."
cd consumer
../consumer-bin > ../consumer-output.log 2>&1 &
CONSUMER_PID=$!
cd ..
echo "  ✓ Consumer running (PID: $CONSUMER_PID)"
sleep 2  # Let consumer connect

# ── Run producer ──────────────────────────────────────────────
echo "[5/5] Starting producer ($TPS TPS, $LIMIT messages)..."
echo
cd producer
../producer-bin -tps="$TPS" -limit="$LIMIT" 2>&1
cd ..
echo

# ── Wait for consumer to finish processing ────────────────────
echo "Waiting 10s for consumer to finish processing..."
sleep 10

# ── Show results ──────────────────────────────────────────────
echo
echo "══════════════════════════════════════════════════"
echo "  Results"
echo "══════════════════════════════════════════════════"

# Check Redis keys
REDIS_KEYS=$(docker exec upi-fraud-detector-redis-1 redis-cli DBSIZE 2>/dev/null | awk '{print $2}')
echo "  Redis user profiles: ${REDIS_KEYS:-0}"

# Check a sample Redis key
SAMPLE_KEY=$(docker exec upi-fraud-detector-redis-1 redis-cli RANDOMKEY 2>/dev/null)
if [ -n "$SAMPLE_KEY" ]; then
    echo "  Sample baseline ($SAMPLE_KEY):"
    docker exec upi-fraud-detector-redis-1 redis-cli HGETALL "$SAMPLE_KEY" 2>/dev/null | head -20
fi

# Check Kafka topics
echo
echo "  Kafka topics:"
docker exec upi-fraud-detector-kafka-1 /opt/kafka/bin/kafka-topics.sh \
    --bootstrap-server localhost:9092 --list 2>/dev/null | grep -v '^__' || true

# Show last lines of consumer output
echo
echo "  Consumer output (last 20 lines):"
tail -20 consumer-output.log 2>/dev/null || echo "  (no output)"

# Cleanup
echo
echo "Stopping consumer..."
kill $CONSUMER_PID 2>/dev/null || true
wait $CONSUMER_PID 2>/dev/null || true
echo "  ✓ Consumer stopped"

# Cleanup binaries
rm -f producer-bin consumer-bin

echo
echo "══════════════════════════════════════════════════"
echo "  ✓ Benchmark complete!"
echo "══════════════════════════════════════════════════"
