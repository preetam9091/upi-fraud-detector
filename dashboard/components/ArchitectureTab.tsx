"use client";

const NODES = [
  { id: "sim",      label: "PaySim\nSimulator",   sub: "Python · 400K txns",      x: 60,  y: 200, color: "#6366f1" },
  { id: "kafka",    label: "Kafka",                sub: "Apache · Topic: txns",     x: 240, y: 200, color: "#f59e0b" },
  { id: "go",       label: "Go\nConsumer",         sub: "goroutines · 10K msg/s",   x: 420, y: 200, color: "#10b981" },
  { id: "redis",    label: "Redis",                sub: "User velocity counters",   x: 420, y: 340, color: "#ef4444" },
  { id: "fastapi",  label: "FastAPI\nScorer",      sub: "XGBoost · SHAP · <20ms",  x: 600, y: 200, color: "#8b5cf6" },
  { id: "supabase", label: "Supabase\nPostgreSQL", sub: "Audit log · every txn",   x: 600, y: 340, color: "#06b6d4" },
  { id: "dash",     label: "Next.js\nDashboard",  sub: "Vercel · Live feed",       x: 780, y: 200, color: "#f97316" },
];

const EDGES = [
  { from: "sim",     to: "kafka",    label: "produce" },
  { from: "kafka",   to: "go",       label: "consume" },
  { from: "go",      to: "redis",    label: "counters" },
  { from: "go",      to: "fastapi",  label: "score" },
  { from: "fastapi", to: "supabase", label: "audit log" },
  { from: "fastapi", to: "dash",     label: "REST API" },
];

function getCenter(id: string) {
  const n = NODES.find(n => n.id === id)!;
  return { x: n.x + 60, y: n.y + 36 };
}

export default function ArchitectureTab() {
  const W = 900, H = 440;

  return (
    <div>
      <div style={{ background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 16, padding: 32, marginBottom: 24 }}>
        <h2 style={{ fontSize: 16, fontWeight: 600, marginBottom: 8 }}>System Architecture</h2>
        <p style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 28 }}>
          Full-stack fraud detection pipeline — every component deployed and running.
        </p>

        <div style={{ overflowX: "auto" }}>
          <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", maxWidth: W, height: "auto", minWidth: 600 }}>
            <defs>
              <marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
                <path d="M0,0 L0,6 L8,3 z" fill="#374151" />
              </marker>
              {NODES.map(n => (
                <filter key={n.id} id={`glow-${n.id}`} x="-50%" y="-50%" width="200%" height="200%">
                  <feDropShadow dx="0" dy="0" stdDeviation="6" floodColor={n.color} floodOpacity="0.4" />
                </filter>
              ))}
            </defs>

            {/* Edges */}
            {EDGES.map((e, i) => {
              const from = getCenter(e.from);
              const to   = getCenter(e.to);
              const mx   = (from.x + to.x) / 2;
              const my   = (from.y + to.y) / 2;
              return (
                <g key={i}>
                  <line
                    x1={from.x} y1={from.y} x2={to.x} y2={to.y}
                    stroke="#374151" strokeWidth="1.5"
                    strokeDasharray={e.from === "go" && e.to === "redis" ? "4 3" : undefined}
                    markerEnd="url(#arrow)"
                  />
                  <text x={mx} y={my - 6} textAnchor="middle"
                    fill="#6b7280" fontSize="10" fontFamily="Inter, sans-serif">
                    {e.label}
                  </text>
                </g>
              );
            })}

            {/* Nodes */}
            {NODES.map(n => (
              <g key={n.id} transform={`translate(${n.x},${n.y})`}>
                <rect
                  width="120" height="72" rx="12"
                  fill="#0d1117" stroke={n.color} strokeWidth="1.5"
                  filter={`url(#glow-${n.id})`}
                />
                <text
                  x="60" y="26"
                  textAnchor="middle" fill={n.color}
                  fontSize="12" fontWeight="700" fontFamily="Inter, sans-serif"
                >
                  {n.label.split("\n").map((line, i) => (
                    <tspan key={i} x="60" dy={i === 0 ? 0 : 14}>{line}</tspan>
                  ))}
                </text>
                <text
                  x="60" y={n.label.includes("\n") ? 56 : 46}
                  textAnchor="middle" fill="#6b7280"
                  fontSize="9" fontFamily="Inter, sans-serif"
                >
                  {n.sub}
                </text>
              </g>
            ))}
          </svg>
        </div>
      </div>

      {/* Stack cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: 14 }}>
        {[
          { name: "Data Generation", items: ["Python", "PaySim model", "400K transactions"], color: "#6366f1" },
          { name: "Stream Processing", items: ["Apache Kafka", "Go consumers", "goroutines"], color: "#f59e0b" },
          { name: "Velocity Cache", items: ["Redis 7", "User counters", "Real-time fan-in/out"], color: "#ef4444" },
          { name: "ML Scoring", items: ["XGBoost", "SHAP explanations", "FastAPI <20ms"], color: "#8b5cf6" },
          { name: "Audit Storage", items: ["Supabase", "PostgreSQL", "Every transaction logged"], color: "#06b6d4" },
          { name: "Dashboard", items: ["Next.js 14", "Recharts", "Vercel (free)"], color: "#f97316" },
        ].map(card => (
          <div key={card.name} style={{
            background: "var(--bg-card)", border: "1px solid var(--border)",
            borderRadius: 12, padding: 16,
            borderLeft: `3px solid ${card.color}`,
          }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: card.color, marginBottom: 10 }}>
              {card.name}
            </div>
            {card.items.map(item => (
              <div key={item} style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 4, display: "flex", alignItems: "center", gap: 6 }}>
                <div style={{ width: 4, height: 4, borderRadius: "50%", background: card.color, flexShrink: 0 }} />
                {item}
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
