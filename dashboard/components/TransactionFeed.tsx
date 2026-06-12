"use client";

import { useEffect, useRef, useState } from "react";
import { RefreshCw } from "lucide-react";

// ── Types ──────────────────────────────────────────────────────────────────
interface Transaction {
  id: string;
  user: string;
  recipient: string;
  amount: number;
  timestamp: string;
  risk_score: number;
  risk_label: string;
  is_fraud: boolean;
  flags: string[];
}

// ── Helpers ────────────────────────────────────────────────────────────────
const RISK_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  LOW:      { bg: "#10b98115", text: "#10b981", border: "#10b98130" },
  MEDIUM:   { bg: "#f59e0b15", text: "#f59e0b", border: "#f59e0b30" },
  HIGH:     { bg: "#f9731615", text: "#f97316", border: "#f9731630" },
  CRITICAL: { bg: "#ef444415", text: "#ef4444", border: "#ef444430" },
};

function riskBadge(label: string) {
  const c = RISK_COLORS[label] || RISK_COLORS.LOW;
  return (
    <span style={{
      padding: "3px 10px", borderRadius: 6,
      background: c.bg, color: c.text,
      border: `1px solid ${c.border}`,
      fontSize: 11, fontWeight: 700, letterSpacing: "0.5px",
    }}>
      {label}
    </span>
  );
}

function scoreBar(score: number) {
  const pct = Math.round(score * 100);
  const color = score >= 0.8 ? "#ef4444" : score >= 0.5 ? "#f97316" : score >= 0.25 ? "#f59e0b" : "#10b981";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <div style={{
        width: 72, height: 5, background: "#1f2937", borderRadius: 999, overflow: "hidden",
      }}>
        <div style={{
          width: `${pct}%`, height: "100%",
          background: color, borderRadius: 999,
          boxShadow: `0 0 6px ${color}`,
        }} />
      </div>
      <span style={{
        fontSize: 12, fontFamily: "'JetBrains Mono', monospace",
        color: color, fontWeight: 500,
      }}>
        {score.toFixed(3)}
      </span>
    </div>
  );
}

// ── Mock transaction generator ─────────────────────────────────────────────
const FRAUD_VPAs   = ["fraud04fb50@ybl","scama53c4e@okicici","mule99@paytm","fake7842@upi"];
const LEGIT_VPAs   = ["zomato@upi","swiggy@icici","amazon@okaxis","netflix@okhdfc","vendor@paytm"];
const USERS        = Array.from({ length: 30 }, (_, i) => `user_${String(i + 1).padStart(4,"0")}`);

let txnSeq = 1;

function makeTxn(forceFraud = false): Transaction {
  const isFraud = forceFraud || Math.random() < 0.05;
  const amount  = isFraud ? 15000 + Math.random() * 40000 : 100 + Math.random() * 3000;
  const score   = isFraud ? 0.75 + Math.random() * 0.25 : Math.random() * 0.2;
  const label   = score >= 0.8 ? "CRITICAL" : score >= 0.5 ? "HIGH" : score >= 0.25 ? "MEDIUM" : "LOW";

  const flags: string[] = [];
  if (isFraud) {
    if (Math.random() > 0.3) flags.push("HIGH_AMOUNT_VS_HISTORY");
    if (Math.random() > 0.4) flags.push("NEW_DEVICE");
    if (Math.random() > 0.5) flags.push("FIRST_TIME_RECIPIENT");
    if (Math.random() > 0.6) flags.push("HIGH_SENDER_FAN_OUT");
  }

  return {
    id: `TXN-${String(txnSeq++).padStart(6, "0")}`,
    user: USERS[Math.floor(Math.random() * USERS.length)],
    recipient: isFraud
      ? FRAUD_VPAs[Math.floor(Math.random() * FRAUD_VPAs.length)]
      : LEGIT_VPAs[Math.floor(Math.random() * LEGIT_VPAs.length)],
    amount: Math.round(amount * 100) / 100,
    timestamp: new Date().toISOString(),
    risk_score: Math.round(score * 1000) / 1000,
    risk_label: label,
    is_fraud: isFraud,
    flags,
  };
}

// Seed initial 25 transactions
function seedTxns(): Transaction[] {
  const txns: Transaction[] = [];
  for (let i = 0; i < 24; i++) txns.push(makeTxn(false));
  txns.unshift(makeTxn(true)); // at least one fraud in seed
  return txns.reverse();
}

// ── Component ──────────────────────────────────────────────────────────────
export default function TransactionFeed({ apiUrl }: { apiUrl: string }) {
  const [transactions, setTransactions] = useState<Transaction[]>(() => seedTxns());
  const [newId, setNewId] = useState<string | null>(null);
  const [paused, setPaused] = useState(false);
  const pausedRef = useRef(false);

  useEffect(() => { pausedRef.current = paused; }, [paused]);

  // Auto-add a new transaction every 2.5 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      if (pausedRef.current) return;
      const txn = makeTxn();
      setNewId(txn.id);
      setTransactions(prev => [txn, ...prev].slice(0, 50));
      setTimeout(() => setNewId(null), 600);
    }, 2500);
    return () => clearInterval(interval);
  }, []);

  const fraudCount = transactions.filter(t => t.is_fraud).length;

  return (
    <div>
      {/* Toolbar */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <h2 style={{ fontSize: 16, fontWeight: 600, color: "var(--text-primary)" }}>
            Live Transaction Feed
          </h2>
          <span style={{
            padding: "2px 8px", borderRadius: 6, fontSize: 11,
            background: "#ef444415", color: "#ef4444", border: "1px solid #ef444430",
            fontWeight: 600,
          }}>
            {fraudCount} fraud
          </span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ fontSize: 12, color: "var(--text-muted)" }}>
            {transactions.length} transactions
          </span>
          <button
            onClick={() => setPaused(p => !p)}
            style={{
              display: "flex", alignItems: "center", gap: 6,
              padding: "6px 14px", borderRadius: 8,
              background: paused ? "#6366f122" : "transparent",
              border: `1px solid ${paused ? "#6366f1" : "var(--border)"}`,
              color: paused ? "#6366f1" : "var(--text-muted)",
              cursor: "pointer", fontSize: 12, fontWeight: 500,
              transition: "all 0.2s",
            }}
          >
            <RefreshCw size={13} style={{ animation: paused ? "none" : "spin 2s linear infinite" }} />
            {paused ? "Resume" : "Pause"}
          </button>
        </div>
      </div>

      {/* Table */}
      <div style={{
        background: "var(--bg-card)", border: "1px solid var(--border)",
        borderRadius: 16, overflow: "hidden",
      }}>
        {/* Header */}
        <div style={{
          display: "grid",
          gridTemplateColumns: "1.4fr 1.6fr 0.9fr 1.1fr 0.9fr 1.5fr",
          padding: "10px 20px",
          background: "var(--bg-card2)",
          borderBottom: "1px solid var(--border)",
          fontSize: 11, fontWeight: 600,
          color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.8px",
        }}>
          <span>Transaction ID</span>
          <span>Recipient VPA</span>
          <span>Amount</span>
          <span>Risk Score</span>
          <span>Label</span>
          <span>Flags</span>
        </div>

        {/* Rows */}
        <div style={{ maxHeight: 520, overflowY: "auto" }}>
          {transactions.map(txn => (
            <div
              key={txn.id}
              className={txn.id === newId ? "animate-slide-in" : ""}
              style={{
                display: "grid",
                gridTemplateColumns: "1.4fr 1.6fr 0.9fr 1.1fr 0.9fr 1.5fr",
                padding: "12px 20px",
                borderBottom: "1px solid var(--border)",
                alignItems: "center",
                background: txn.is_fraud
                  ? "linear-gradient(90deg, #ef444408 0%, transparent 100%)"
                  : "transparent",
                transition: "background 0.2s",
              }}
              onMouseOver={e => {
                if (!txn.is_fraud)
                  (e.currentTarget as HTMLDivElement).style.background = "var(--bg-card2)";
              }}
              onMouseOut={e => {
                (e.currentTarget as HTMLDivElement).style.background = txn.is_fraud
                  ? "linear-gradient(90deg, #ef444408 0%, transparent 100%)"
                  : "transparent";
              }}
            >
              <span style={{
                fontSize: 12, fontFamily: "'JetBrains Mono', monospace",
                color: "var(--text-muted)",
              }}>
                {txn.id}
              </span>
              <span style={{ fontSize: 12, color: "var(--text-primary)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {txn.recipient}
              </span>
              <span style={{
                fontSize: 13, fontWeight: 600,
                color: txn.amount > 10000 ? "#f59e0b" : "var(--text-primary)",
              }}>
                ₹{txn.amount.toLocaleString("en-IN")}
              </span>
              {scoreBar(txn.risk_score)}
              {riskBadge(txn.risk_label)}
              <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                {txn.flags.slice(0, 2).map(f => (
                  <span key={f} style={{
                    fontSize: 10, padding: "2px 6px", borderRadius: 4,
                    background: "#ef444415", color: "#ef4444",
                    border: "1px solid #ef444425",
                    whiteSpace: "nowrap",
                  }}>
                    {f.replace(/_/g, " ")}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      <p style={{ marginTop: 12, fontSize: 11, color: "var(--text-muted)", textAlign: "center" }}>
        Simulated live feed · New transactions every 2.5s · Up to 50 shown
      </p>
    </div>
  );
}
