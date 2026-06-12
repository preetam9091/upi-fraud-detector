package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"math"
	"os"
	"sort"
	"strconv"
	"time"

	"github.com/joho/godotenv"
	"github.com/redis/go-redis/v9"
	kafka "github.com/segmentio/kafka-go"
)

// ── Data structures ──────────────────────────────────────────────────────────

type Transaction struct {
	TxnID               string  `json:"txn_id"`
	UserID              string  `json:"user_id"`
	Timestamp           string  `json:"timestamp"`
	Amount              float64 `json:"amount"`
	Category            string  `json:"category"`
	DeviceID            string  `json:"device_id"`
	City                string  `json:"city"`
	RecipientVPA        string  `json:"recipient_vpa"`
	RecipientSeenBefore bool    `json:"recipient_seen_before"`
	IsFestivalDay       bool    `json:"is_festival_day"`
	IsFraud             bool    `json:"is_fraud"`
}

type ScoredTransaction struct {
	Transaction
	RiskScore int    `json:"risk_score"`
	RiskLevel string `json:"risk_level"`
	Signals   string `json:"signals"`
}

type FraudAlert struct {
	TxnID     string  `json:"txn_id"`
	UserID    string  `json:"user_id"`
	Amount    float64 `json:"amount"`
	RiskScore int     `json:"risk_score"`
	Signals   string  `json:"signals"`
	Timestamp string  `json:"timestamp"`
	AlertedAt string  `json:"alerted_at"`
}

type UserBaseline struct {
	// Welford's online stats
	Mean  float64
	M2    float64
	Count float64
	// Behavioral
	LastTS        int64
	PrimaryDevice string
	LastCity      string
	// Daily velocity
	TxnCountToday int
	TxnDate       string // "2024-01-15" — resets when date changes
}

// ── Redis baseline read/write ────────────────────────────────────────────────

func getBaseline(ctx context.Context, rdb *redis.Client, userID string) UserBaseline {
	vals, err := rdb.HGetAll(ctx, "user:"+userID).Result()
	if err != nil || len(vals) == 0 {
		return UserBaseline{}
	}

	b := UserBaseline{}
	if v, ok := vals["mean"]; ok {
		b.Mean, _ = strconv.ParseFloat(v, 64)
	}
	if v, ok := vals["m2"]; ok {
		b.M2, _ = strconv.ParseFloat(v, 64)
	}
	if v, ok := vals["count"]; ok {
		b.Count, _ = strconv.ParseFloat(v, 64)
	}
	if v, ok := vals["last_ts"]; ok {
		b.LastTS, _ = strconv.ParseInt(v, 10, 64)
	}
	if v, ok := vals["device"]; ok {
		b.PrimaryDevice = v
	}
	if v, ok := vals["last_city"]; ok {
		b.LastCity = v
	}
	if v, ok := vals["txn_count_today"]; ok {
		b.TxnCountToday, _ = strconv.Atoi(v)
	}
	if v, ok := vals["txn_date"]; ok {
		b.TxnDate = v
	}

	return b
}

func updateBaseline(ctx context.Context, rdb *redis.Client, userID string,
	b UserBaseline, amount float64, deviceID, city string, nowTS int64) {

	// Welford's online algorithm — running mean + variance in one pass
	b.Count++
	delta := amount - b.Mean
	b.Mean += delta / b.Count
	b.M2 += delta * (amount - b.Mean)

	// Primary device: keep the first device seen
	device := b.PrimaryDevice
	if device == "" {
		device = deviceID
	}

	// Daily transaction count — reset if the date has changed
	today := time.Unix(nowTS, 0).Format("2006-01-02")
	if b.TxnDate == today {
		b.TxnCountToday++
	} else {
		b.TxnCountToday = 1
		b.TxnDate = today
	}

	rdb.HSet(ctx, "user:"+userID,
		"mean", fmt.Sprintf("%.4f", b.Mean),
		"m2", fmt.Sprintf("%.4f", b.M2),
		"count", fmt.Sprintf("%.0f", b.Count),
		"last_ts", fmt.Sprintf("%d", nowTS),
		"device", device,
		"last_city", city,
		"txn_count_today", fmt.Sprintf("%d", b.TxnCountToday),
		"txn_date", today,
	)
	rdb.Expire(ctx, "user:"+userID, 90*24*time.Hour)
}

// ── Risk scoring ─────────────────────────────────────────────────────────────

func computeRiskScore(txn Transaction, b UserBaseline, nowTS int64) (int, string, string) {
	score := 0
	signals := ""

	// Signal 1: Amount z-score > 3 (way above this user's normal)
	if b.Count > 1 {
		variance := b.M2 / (b.Count - 1)
		std := math.Sqrt(variance)
		if std > 0 {
			zscore := (txn.Amount - b.Mean) / std
			if zscore > 3 {
				score++
				signals += "high_zscore,"
			}
		}
	}

	// Signal 2: New device never seen before
	if b.PrimaryDevice != "" && txn.DeviceID != b.PrimaryDevice {
		score++
		signals += "new_device,"
	}

	// Signal 3: Odd hour (midnight–5am)
	t, err := time.Parse("2006-01-02T15:04:05", txn.Timestamp)
	if err == nil && t.Hour() >= 0 && t.Hour() <= 5 {
		score++
		signals += "odd_hour,"
	}

	// Signal 4: Never sent to this recipient before
	if !txn.RecipientSeenBefore {
		score++
		signals += "new_recipient,"
	}

	// Signal 5: Threshold gaming (just below ₹50k)
	if txn.Amount >= 45000 && txn.Amount <= 49999 {
		score++
		signals += "threshold_gaming,"
	}

	// Signal 6: City changed from baseline (location anomaly)
	if b.LastCity != "" && txn.City != b.LastCity {
		score++
		signals += "city_change,"
	}

	// Signal 7: Velocity — more than 10 transactions today
	if b.TxnCountToday > 10 {
		score++
		signals += "high_velocity,"
	}

	// Trim trailing comma
	if len(signals) > 0 {
		signals = signals[:len(signals)-1]
	}

	var level string
	switch {
	case score >= 4:
		level = "🔴 HIGH  "
	case score >= 2:
		level = "🟡 MEDIUM"
	default:
		level = "🟢 LOW   "
	}

	return score, level, signals
}

// ── Latency stats ────────────────────────────────────────────────────────────

type LatencyTracker struct {
	samples []float64
}

func (lt *LatencyTracker) Add(d time.Duration) {
	lt.samples = append(lt.samples, float64(d.Microseconds()))
}

func (lt *LatencyTracker) Stats() (p50, p99, avg float64) {
	n := len(lt.samples)
	if n == 0 {
		return 0, 0, 0
	}

	sorted := make([]float64, n)
	copy(sorted, lt.samples)
	sort.Float64s(sorted)

	p50 = sorted[n*50/100]
	p99 = sorted[n*99/100]

	sum := 0.0
	for _, v := range sorted {
		sum += v
	}
	avg = sum / float64(n)

	return p50, p99, avg
}

func (lt *LatencyTracker) Reset() {
	lt.samples = lt.samples[:0]
}

// ── Main ─────────────────────────────────────────────────────────────────────

func main() {
	if err := godotenv.Load("../../.env"); err != nil {
		log.Fatal("Cannot load .env")
	}

	broker := os.Getenv("KAFKA_BROKER")
	redisURL := os.Getenv("REDIS_URL")

	// ── Connect to Redis ─────────────────────────────────────────────────
	opts, err := redis.ParseURL(redisURL)
	if err != nil {
		log.Fatal("Redis URL error:", err)
	}
	rdb := redis.NewClient(opts)
	ctx := context.Background()

	if _, err := rdb.Ping(ctx).Result(); err != nil {
		log.Fatal("Redis connection failed:", err)
	}
	fmt.Println("✓ Redis connected")

	// ── Connect to Kafka — consumer ──────────────────────────────────────
	reader := kafka.NewReader(kafka.ReaderConfig{
		Brokers:  []string{broker},
		Topic:    "raw-transactions",
		GroupID:  "fraud-consumer-v1",
		MinBytes: 1e3,
		MaxBytes: 10e6,
	})
	defer reader.Close()

	// ── Kafka writers for output topics ──────────────────────────────────
	scoredWriter := &kafka.Writer{
		Addr:                   kafka.TCP(broker),
		Topic:                  "scored-transactions",
		AllowAutoTopicCreation: true,
		Balancer:               &kafka.RoundRobin{},
		BatchSize:              100,
		BatchTimeout:           5 * time.Millisecond,
		RequiredAcks:           kafka.RequireOne,
	}
	defer scoredWriter.Close()

	alertWriter := &kafka.Writer{
		Addr:                   kafka.TCP(broker),
		Topic:                  "fraud-alerts",
		AllowAutoTopicCreation: true,
		Balancer:               &kafka.RoundRobin{},
		BatchSize:              1, // Alerts are rare — flush immediately
		BatchTimeout:           1 * time.Millisecond,
		RequiredAcks:           kafka.RequireOne,
	}
	defer alertWriter.Close()

	fmt.Println("✓ Kafka consumer connected")
	fmt.Println("✓ Kafka writers ready (scored-transactions, fraud-alerts)")
	fmt.Println("⟳ Listening for transactions...\n")
	fmt.Printf("%-10s %-10s %-12s %-10s %-6s  %s\n",
		"TIME", "TXN_ID", "AMOUNT", "RISK", "SCORE", "SIGNALS")
	fmt.Println("────────────────────────────────────────────────────────────────────")

	processed := 0
	highRisk := 0
	mediumRisk := 0
	start := time.Now()
	latency := &LatencyTracker{}

	for {
		msg, err := reader.ReadMessage(ctx)
		if err != nil {
			log.Printf("Read error: %v", err)
			continue
		}

		msgStart := time.Now()

		var txn Transaction
		if err := json.Unmarshal(msg.Value, &txn); err != nil {
			continue
		}

		nowTS := time.Now().Unix()

		// 1. Read baseline from Redis
		baseline := getBaseline(ctx, rdb, txn.UserID)

		// 2. Compute risk score
		score, level, signals := computeRiskScore(txn, baseline, nowTS)

		// 3. Update baseline in Redis
		updateBaseline(ctx, rdb, txn.UserID, baseline, txn.Amount, txn.DeviceID, txn.City, nowTS)

		// 4. Publish scored transaction
		scored := ScoredTransaction{
			Transaction: txn,
			RiskScore:   score,
			RiskLevel:   level,
			Signals:     signals,
		}
		scoredData, _ := json.Marshal(scored)
		scoredWriter.WriteMessages(ctx, kafka.Message{
			Key:   []byte(txn.UserID),
			Value: scoredData,
		})

		// 5. Publish fraud alert if HIGH risk
		if score >= 4 {
			alert := FraudAlert{
				TxnID:     txn.TxnID,
				UserID:    txn.UserID,
				Amount:    txn.Amount,
				RiskScore: score,
				Signals:   signals,
				Timestamp: txn.Timestamp,
				AlertedAt: time.Now().Format(time.RFC3339),
			}
			alertData, _ := json.Marshal(alert)
			alertWriter.WriteMessages(ctx, kafka.Message{
				Key:   []byte(txn.UserID),
				Value: alertData,
			})
		}

		// Track latency
		latency.Add(time.Since(msgStart))

		processed++
		if score >= 4 {
			highRisk++
		} else if score >= 2 {
			mediumRisk++
		}

		// Print HIGH risk always | print every 200th otherwise
		if score >= 4 || processed%200 == 0 {
			tps := float64(processed) / time.Since(start).Seconds()
			fmt.Printf("%-10s %-10s ₹%-11.0f %s  %d      %s  (tps=%.0f)\n",
				time.Now().Format("15:04:05"),
				txn.TxnID[:8],
				txn.Amount,
				level,
				score,
				signals,
				tps,
			)
		}

		// Print latency stats every 1000 messages
		if processed%1000 == 0 {
			p50, p99, avg := latency.Stats()
			tps := float64(processed) / time.Since(start).Seconds()
			fmt.Println()
			fmt.Println("  ╔══════════════════════════════════════════════════════╗")
			fmt.Printf("  ║  Processed: %6d | High: %4d | Medium: %4d       ║\n",
				processed, highRisk, mediumRisk)
			fmt.Printf("  ║  TPS: %7.1f                                       ║\n", tps)
			fmt.Printf("  ║  Latency p50: %6.0fµs | p99: %6.0fµs | avg: %6.0fµs ║\n",
				p50, p99, avg)
			fmt.Println("  ╚══════════════════════════════════════════════════════╝")
			fmt.Println()
			latency.Reset()
		}
	}
}