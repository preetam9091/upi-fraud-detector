"use client";

import { useEffect, useState } from "react";
import { TrendingUp, ShieldAlert, Activity, Percent } from "lucide-react";

interface Stat {
  label: string;
  value: string;
  sub: string;
  icon: React.ReactNode;
  color: string;
  glow: string;
}

function useCountUp(target: number, duration = 1200) {
  const [val, setVal] = useState(0);
  useEffect(() => {
    const start = Date.now();
    const tick = () => {
      const p = Math.min((Date.now() - start) / duration, 1);
      setVal(Math.floor(p * target));
      if (p < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }, [target, duration]);
  return val;
}

function StatCard({ stat }: { stat: Stat }) {
  return (
    <div style={{
      background: "var(--bg-card)",
      border: "1px solid var(--border)",
      borderRadius: 16,
      padding: "20px 24px",
      display: "flex",
      alignItems: "center",
      gap: 16,
      flex: 1,
      minWidth: 200,
      position: "relative",
      overflow: "hidden",
      transition: "transform 0.2s, box-shadow 0.2s",
    }}
    onMouseOver={e => {
      (e.currentTarget as HTMLDivElement).style.transform = "translateY(-2px)";
      (e.currentTarget as HTMLDivElement).style.boxShadow = `0 8px 32px ${stat.glow}`;
    }}
    onMouseOut={e => {
      (e.currentTarget as HTMLDivElement).style.transform = "translateY(0)";
      (e.currentTarget as HTMLDivElement).style.boxShadow = "none";
    }}
    >
      {/* Gradient orb */}
      <div style={{
        position: "absolute", top: -20, right: -20,
        width: 80, height: 80, borderRadius: "50%",
        background: stat.glow, filter: "blur(30px)", opacity: 0.4,
      }} />

      <div style={{
        width: 44, height: 44, borderRadius: 12,
        background: `${stat.glow}22`,
        border: `1px solid ${stat.glow}44`,
        display: "flex", alignItems: "center", justifyContent: "center",
        color: stat.color, flexShrink: 0,
      }}>
        {stat.icon}
      </div>

      <div>
        <div style={{ fontSize: 24, fontWeight: 700, color: stat.color, lineHeight: 1 }}>
          {stat.value}
        </div>
        <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 4 }}>
          {stat.label}
        </div>
        <div style={{ fontSize: 11, color: stat.color, marginTop: 2, opacity: 0.8 }}>
          {stat.sub}
        </div>
      </div>
    </div>
  );
}

export default function StatsBar() {
  // Simulated live stats — in production these come from Supabase
  const txnCount  = useCountUp(12847);
  const fraudCount = useCountUp(48);

  const stats: Stat[] = [
    {
      label: "Transactions Today",
      value: txnCount.toLocaleString(),
      sub: "+214 in last hour",
      icon: <Activity size={20} />,
      color: "#6366f1",
      glow: "#6366f1",
    },
    {
      label: "Fraud Detected",
      value: fraudCount.toString(),
      sub: "0.37% fraud rate",
      icon: <ShieldAlert size={20} />,
      color: "#ef4444",
      glow: "#ef4444",
    },
    {
      label: "Avg Risk Score",
      value: "0.031",
      sub: "Model well-calibrated",
      icon: <TrendingUp size={20} />,
      color: "#10b981",
      glow: "#10b981",
    },
    {
      label: "False Positive Rate",
      value: "0.12%",
      sub: "High precision maintained",
      icon: <Percent size={20} />,
      color: "#f59e0b",
      glow: "#f59e0b",
    },
  ];

  return (
    <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
      {stats.map(s => <StatCard key={s.label} stat={s} />)}
    </div>
  );
}
