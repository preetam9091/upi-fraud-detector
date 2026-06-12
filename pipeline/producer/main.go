package main

import (
	"context"
	"encoding/csv"
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"os"
	"strconv"
	"time"

	"github.com/joho/godotenv"
	kafka "github.com/segmentio/kafka-go"
)

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

func main() {
	// Configurable flags
	tpsFlag := flag.Int("tps", 1000, "transactions per second")
	limitFlag := flag.Int("limit", 50000, "max transactions to publish")
	flag.Parse()

	tps := *tpsFlag
	limit := *limitFlag

	if err := godotenv.Load("../../.env"); err != nil {
		log.Fatal("Cannot load .env")
	}

	broker := os.Getenv("KAFKA_BROKER")

	// kafka.Writer with explicit batch settings to prevent hanging.
	// BatchSize=1 + short BatchTimeout ensures messages are sent immediately
	// instead of waiting for a full batch (which caused the previous hang).
	writer := &kafka.Writer{
		Addr:                   kafka.TCP(broker),
		Topic:                  "raw-transactions",
		AllowAutoTopicCreation: true,
		Balancer:               &kafka.RoundRobin{},
		BatchSize:              100,
		BatchTimeout:           5 * time.Millisecond,
		WriteTimeout:           10 * time.Second,
		ReadTimeout:            10 * time.Second,
		RequiredAcks:           kafka.RequireOne,
	}
	defer writer.Close()

	// Open transactions CSV
	file, err := os.Open("../../data/transactions.csv")
	if err != nil {
		log.Fatal("Cannot open transactions.csv:", err)
	}
	defer file.Close()

	reader := csv.NewReader(file)
	reader.Read() // skip header

	// Ticker for target TPS
	ticker := time.NewTicker(time.Second / time.Duration(tps))
	defer ticker.Stop()

	ctx := context.Background()
	count := 0
	errors := 0
	startTime := time.Now()

	fmt.Println("══════════════════════════════════════════════════")
	fmt.Printf("  UPI Fraud Producer — %d TPS (limit: %d)\n", tps, limit)
	fmt.Println("══════════════════════════════════════════════════")
	fmt.Println()

	// Pre-read a batch of rows for efficiency
	batch := make([]kafka.Message, 0, 100)
	lastPrinted := 0

	for count < limit {
		row, err := reader.Read()
		if err != nil {
			break
		}

		<-ticker.C

		amount, _ := strconv.ParseFloat(row[3], 64)

		txn := Transaction{
			TxnID:               row[0],
			UserID:              row[1],
			Timestamp:           row[2],
			Amount:              amount,
			Category:            row[4],
			DeviceID:            row[5],
			City:                row[6],
			RecipientVPA:        row[7],
			RecipientSeenBefore: row[8] == "True",
			IsFestivalDay:       row[9] == "True",
			IsFraud:             row[10] == "True",
		}

		data, _ := json.Marshal(txn)

		batch = append(batch, kafka.Message{
			Key:   []byte(txn.UserID),
			Value: data,
		})

		// Flush batch every 100 messages or at the end
		if len(batch) >= 100 || count+len(batch) >= limit {
			if err := writer.WriteMessages(ctx, batch...); err != nil {
				log.Printf("Write error: %v", err)
				errors += len(batch)
			}
			count += len(batch)
			batch = batch[:0]

			// Print progress at every 1000 boundary (only once)
			if count/1000 > lastPrinted {
				lastPrinted = count / 1000
				elapsed := time.Since(startTime).Seconds()
				fmt.Printf("  [%s] Published %6d | TPS: %7.1f | errors: %d\n",
					time.Now().Format("15:04:05"), count, float64(count)/elapsed, errors)
			}
		}
	}

	// Flush remaining
	if len(batch) > 0 {
		if err := writer.WriteMessages(ctx, batch...); err != nil {
			log.Printf("Write error: %v", err)
			errors += len(batch)
		}
		count += len(batch)
	}

	elapsed := time.Since(startTime).Seconds()
	fmt.Println()
	fmt.Println("══════════════════════════════════════════════════")
	fmt.Printf("  ✓ Done! %d messages in %.1fs (%.1f TPS)\n", count, elapsed, float64(count)/elapsed)
	fmt.Printf("  ✗ Errors: %d\n", errors)
	fmt.Println("══════════════════════════════════════════════════")
}