"use client";

import { useState } from "react";
import StatsBar from "@/components/StatsBar";
import TransactionFeed from "@/components/TransactionFeed";
import TryItPanel from "@/components/TryItPanel";
import RiskChart from "@/components/RiskChart";
import ArchitectureTab from "@/components/ArchitectureTab";
import { Activity, Zap, BarChart2, GitBranch } from "lucide-react";

const TABS = [
  { id: "live",   label: "Live Feed",      icon: Activity },
  { id: "try",    label: "Try It",         icon: Zap },
  { id: "chart",  label: "Risk Chart",     icon: BarChart2 },
  { id: "arch",   label: "Architecture",   icon: GitBranch },
];

const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://upi-fraud-detector-production.up.railway.app";

export default function Home() {
  const [activeTab, setActiveTab] = useState("live");

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg-primary)" }}>
      {/* ── HEADER ─────────────────────────────────────────────── */}
      <header style={{
        borderBottom: "1px solid var(--border)",
        background: "rgba(13,17,23,0.95)",
        backdropFilter: "blur(12px)",
        position: "sticky", top: 0, zIndex: 50,
      }}>
        <div style={{ maxWidth: 1280, margin: "0 auto", padding: "0 24px" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", height: 64 }}>
            {/* Logo */}
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <div style={{
                width: 36, height: 36, borderRadius: 10,
                background: "linear-gradient(135deg, #6366f1, #8b5cf6)",
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: 18,
              }}>🛡️</div>
              <div>
                <div style={{ fontWeight: 700, fontSize: 16, color: "var(--text-primary)", letterSpacing: "-0.3px" }}>
                  UPI Fraud Detector
                </div>
                <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 1 }}>
                  Real-time ML scoring · XGBoost + SHAP
                </div>
              </div>
            </div>

            {/* Live indicator + links */}
            <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <div className="live-dot" style={{
                  width: 8, height: 8, borderRadius: "50%",
                  background: "#10b981",
                  boxShadow: "0 0 8px #10b981",
                }} />
                <span style={{ fontSize: 12, color: "#10b981", fontWeight: 600 }}>LIVE</span>
              </div>
              <a
                href={`${API_URL}/docs`}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  fontSize: 12, color: "var(--text-muted)",
                  textDecoration: "none", fontWeight: 500,
                  padding: "6px 14px", borderRadius: 8,
                  border: "1px solid var(--border)",
                  transition: "all 0.2s",
                }}
                onMouseOver={e => {
                  (e.currentTarget as HTMLAnchorElement).style.color = "var(--text-primary)";
                  (e.currentTarget as HTMLAnchorElement).style.borderColor = "#6366f1";
                }}
                onMouseOut={e => {
                  (e.currentTarget as HTMLAnchorElement).style.color = "var(--text-muted)";
                  (e.currentTarget as HTMLAnchorElement).style.borderColor = "var(--border)";
                }}
              >
                API Docs ↗
              </a>
            </div>
          </div>
        </div>
      </header>

      <main style={{ maxWidth: 1280, margin: "0 auto", padding: "32px 24px" }}>
        {/* ── STATS BAR ───────────────────────────────────────── */}
        <StatsBar />

        {/* ── TABS ────────────────────────────────────────────── */}
        <div style={{ marginTop: 32 }}>
          <div style={{
            display: "flex", gap: 4,
            borderBottom: "1px solid var(--border)",
            marginBottom: 28,
          }}>
            {TABS.map(tab => {
              const Icon = tab.icon;
              const active = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  style={{
                    display: "flex", alignItems: "center", gap: 7,
                    padding: "10px 18px",
                    background: "none", border: "none", cursor: "pointer",
                    fontSize: 13, fontWeight: active ? 600 : 500,
                    color: active ? "var(--accent)" : "var(--text-muted)",
                    borderBottom: active ? "2px solid var(--accent)" : "2px solid transparent",
                    marginBottom: -1,
                    transition: "all 0.15s",
                  }}
                >
                  <Icon size={14} />
                  {tab.label}
                </button>
              );
            })}
          </div>

          {/* ── TAB CONTENT ─────────────────────────────────── */}
          <div>
            {activeTab === "live"  && <TransactionFeed apiUrl={API_URL} />}
            {activeTab === "try"   && <TryItPanel apiUrl={API_URL} />}
            {activeTab === "chart" && <RiskChart />}
            {activeTab === "arch"  && <ArchitectureTab />}
          </div>
        </div>
      </main>

      {/* ── FOOTER ──────────────────────────────────────────────── */}
      <footer style={{
        borderTop: "1px solid var(--border)",
        padding: "24px",
        marginTop: 48,
        textAlign: "center",
        color: "var(--text-muted)",
        fontSize: 12,
      }}>
        Built with XGBoost · FastAPI · Kafka · Go · Redis · Next.js &nbsp;·&nbsp;
        <a href={`${API_URL}/docs`} target="_blank" rel="noopener noreferrer"
          style={{ color: "var(--accent)", textDecoration: "none" }}>
          API Reference ↗
        </a>
      </footer>
    </div>
  );
}
