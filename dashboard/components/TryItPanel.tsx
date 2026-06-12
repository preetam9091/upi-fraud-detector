"use client";

import { useState } from "react";
import { Send, Loader2, ShieldAlert, ShieldCheck } from "lucide-react";

interface ScoreResponse {
  transaction_id: string;
  risk_score: number;
  risk_label: string;
  is_fraud: boolean;
  flags: string[];
  shap_top5: { feature: string; value: number; shap_contribution: number; direction: string }[];
  latency_ms: number;
}

const RISK_COLORS: Record<string, string> = {
  LOW: "#10b981", MEDIUM: "#f59e0b", HIGH: "#f97316", CRITICAL: "#ef4444",
};

const PRESETS = {
  fraud: {
    label: "🚨 Fraud Example",
    data: {
      transaction_id: "TXN-DEMO-FRAUD",
      user_id: "user_42",
      recipient_vpa: "fraud04fb50@ybl",
      amount: 24285,
      timestamp: "2025-03-10T19:00:00",
      device_id: "device_brand_new",
      avg_txn_amount: 1080,
      account_age_days: 12,
      user_txn_rank: 42,
      days_since_last_txn: 4.1,
      rolling_mean: 1050,
      rolling_std: 120,
      primary_device: "device_registered_old",
      city_tier: "tier1",
      recipient_fan_in: 1,
      sender_fan_out: 20,
      recipient_seen_before: 0,
      is_festival_day: 0,
    },
  },
  legit: {
    label: "✅ Legit Example",
    data: {
      transaction_id: "TXN-DEMO-LEGIT",
      user_id: "user_regular_99",
      recipient_vpa: "swiggy@icici",
      amount: 350,
      timestamp: "2025-03-10T11:30:00",
      device_id: "my_regular_phone",
      avg_txn_amount: 400,
      account_age_days: 720,
      user_txn_rank: 350,
      days_since_last_txn: 2.0,
      rolling_mean: 380,
      rolling_std: 80,
      primary_device: "my_regular_phone",
      city_tier: "tier1",
      recipient_fan_in: 3,
      sender_fan_out: 2,
      recipient_seen_before: 1,
      is_festival_day: 0,
    },
  },
};

export default function TryItPanel({ apiUrl }: { apiUrl: string }) {
  const [form, setForm] = useState(PRESETS.fraud.data);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ScoreResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const update = (key: string, val: string | number) =>
    setForm(f => ({ ...f, [key]: val }));

  const loadPreset = (preset: keyof typeof PRESETS) => {
    setForm(PRESETS[preset].data);
    setResult(null);
    setError(null);
  };

  const submit = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await fetch(`${apiUrl}/v1/score`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setResult(await res.json());
    } catch (e) {
      setError(`Failed to reach API: ${e}`);
    } finally {
      setLoading(false);
    }
  };

  const riskColor = result ? RISK_COLORS[result.risk_label] ?? "#6366f1" : "#6366f1";

  const Field = ({ label, k, type = "text" }: { label: string; k: string; type?: string }) => (
    <div>
      <label style={{ fontSize: 11, color: "var(--text-muted)", fontWeight: 600, letterSpacing: "0.5px", display: "block", marginBottom: 5 }}>
        {label.toUpperCase()}
      </label>
      <input
        type={type}
        value={(form as Record<string, string | number>)[k]}
        onChange={e => update(k, type === "number" ? parseFloat(e.target.value) : e.target.value)}
        style={{
          width: "100%", padding: "8px 12px",
          background: "var(--bg-primary)", border: "1px solid var(--border)",
          borderRadius: 8, color: "var(--text-primary)", fontSize: 13,
          fontFamily: "'JetBrains Mono', monospace",
          outline: "none", transition: "border-color 0.2s",
        }}
        onFocus={e => (e.target.style.borderColor = "#6366f1")}
        onBlur={e => (e.target.style.borderColor = "var(--border)")}
      />
    </div>
  );

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, alignItems: "start" }}>
      {/* ── FORM ──────────────────────────────────────────── */}
      <div style={{ background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 16, padding: 24 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20 }}>
          <h2 style={{ fontSize: 16, fontWeight: 600 }}>Score a Transaction</h2>
          <div style={{ display: "flex", gap: 8 }}>
            {Object.entries(PRESETS).map(([key, preset]) => (
              <button
                key={key}
                onClick={() => loadPreset(key as keyof typeof PRESETS)}
                style={{
                  padding: "5px 12px", borderRadius: 7, fontSize: 12, fontWeight: 500,
                  background: "var(--bg-card2)", border: "1px solid var(--border)",
                  color: "var(--text-muted)", cursor: "pointer", transition: "all 0.2s",
                }}
                onMouseOver={e => {
                  (e.currentTarget as HTMLButtonElement).style.borderColor = "#6366f1";
                  (e.currentTarget as HTMLButtonElement).style.color = "var(--text-primary)";
                }}
                onMouseOut={e => {
                  (e.currentTarget as HTMLButtonElement).style.borderColor = "var(--border)";
                  (e.currentTarget as HTMLButtonElement).style.color = "var(--text-muted)";
                }}
              >
                {preset.label}
              </button>
            ))}
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
          <Field label="Transaction ID" k="transaction_id" />
          <Field label="User ID"        k="user_id" />
          <Field label="Recipient VPA"  k="recipient_vpa" />
          <Field label="Amount (₹)"     k="amount" type="number" />
          <Field label="Timestamp"      k="timestamp" />
          <Field label="Device ID"      k="device_id" />
          <Field label="Primary Device" k="primary_device" />
          <Field label="Avg Txn Amount" k="avg_txn_amount" type="number" />
          <Field label="Account Age (days)" k="account_age_days" type="number" />
          <Field label="Txn Rank"       k="user_txn_rank" type="number" />
          <Field label="Days Since Last" k="days_since_last_txn" type="number" />
          <Field label="Sender Fan-Out" k="sender_fan_out" type="number" />
          <Field label="Recipient Fan-In" k="recipient_fan_in" type="number" />
          <Field label="City Tier"      k="city_tier" />
        </div>

        <button
          onClick={submit}
          disabled={loading}
          style={{
            marginTop: 20, width: "100%", padding: "12px 0",
            background: loading ? "var(--bg-card2)" : "linear-gradient(135deg, #6366f1, #8b5cf6)",
            border: "none", borderRadius: 10,
            color: "white", fontSize: 14, fontWeight: 600, cursor: loading ? "not-allowed" : "pointer",
            display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
            transition: "opacity 0.2s",
            opacity: loading ? 0.7 : 1,
          }}
        >
          {loading ? <><Loader2 size={16} style={{ animation: "spin 1s linear infinite" }} /> Scoring...</>
                   : <><Send size={15} /> Score Transaction</>}
        </button>
      </div>

      {/* ── RESULT ────────────────────────────────────────── */}
      <div style={{ background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 16, padding: 24, minHeight: 400 }}>
        {!result && !error && !loading && (
          <div style={{ height: "100%", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 12, opacity: 0.4, paddingTop: 80 }}>
            <ShieldCheck size={48} color="#6366f1" />
            <p style={{ color: "var(--text-muted)", fontSize: 14 }}>Score a transaction to see results</p>
          </div>
        )}

        {error && (
          <div style={{ padding: 16, background: "#ef444415", border: "1px solid #ef444430", borderRadius: 10, color: "#ef4444", fontSize: 13 }}>
            {error}
          </div>
        )}

        {result && (
          <div className="animate-slide-in">
            {/* Score header */}
            <div style={{
              padding: 20, borderRadius: 12, marginBottom: 20,
              background: `${riskColor}10`,
              border: `1px solid ${riskColor}30`,
              display: "flex", alignItems: "center", gap: 16,
            }}>
              {result.is_fraud
                ? <ShieldAlert size={32} color={riskColor} />
                : <ShieldCheck size={32} color={riskColor} />
              }
              <div>
                <div style={{ fontSize: 28, fontWeight: 800, color: riskColor, lineHeight: 1 }}>
                  {(result.risk_score * 100).toFixed(1)}%
                </div>
                <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 3 }}>
                  Risk Score · <span style={{ color: riskColor, fontWeight: 700 }}>{result.risk_label}</span>
                  {" · "}{result.is_fraud ? "⚠ FRAUD" : "✓ LEGIT"}
                </div>
                <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 2 }}>
                  Scored in {result.latency_ms.toFixed(1)}ms
                </div>
              </div>
            </div>

            {/* Flags */}
            {result.flags.length > 0 && (
              <div style={{ marginBottom: 16 }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: "var(--text-muted)", marginBottom: 8, letterSpacing: "0.5px" }}>
                  TRIGGERED FLAGS
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                  {result.flags.map(f => (
                    <span key={f} style={{
                      padding: "3px 10px", borderRadius: 6, fontSize: 11, fontWeight: 600,
                      background: "#ef444415", color: "#ef4444", border: "1px solid #ef444430",
                    }}>
                      {f.replace(/_/g, " ")}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* SHAP */}
            <div>
              <div style={{ fontSize: 11, fontWeight: 700, color: "var(--text-muted)", marginBottom: 10, letterSpacing: "0.5px" }}>
                TOP 5 SHAP EXPLANATIONS
              </div>
              {result.shap_top5.map((s, i) => {
                const pct = Math.min(Math.abs(s.shap_contribution) / 15 * 100, 100);
                const col = s.shap_contribution > 0 ? "#ef4444" : "#10b981";
                return (
                  <div key={i} style={{ marginBottom: 10 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                      <span style={{ fontSize: 12, fontFamily: "'JetBrains Mono',monospace", color: "var(--text-primary)" }}>
                        {s.feature}
                      </span>
                      <span style={{ fontSize: 11, color: col, fontWeight: 600 }}>
                        {s.shap_contribution > 0 ? "+" : ""}{s.shap_contribution.toFixed(3)}
                      </span>
                    </div>
                    <div style={{ height: 4, background: "#1f2937", borderRadius: 999 }}>
                      <div style={{
                        height: "100%", width: `${pct}%`,
                        background: col, borderRadius: 999,
                        boxShadow: `0 0 6px ${col}`,
                        transition: "width 0.6s ease",
                      }} />
                    </div>
                    <div style={{ fontSize: 10, color: "var(--text-muted)", marginTop: 2 }}>
                      {s.direction} · value = {s.value}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>

      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
