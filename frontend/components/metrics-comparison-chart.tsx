"use client";

import { Bar, BarChart, ResponsiveContainer, XAxis, YAxis, Tooltip, Legend, CartesianGrid } from "recharts";

export function MetricsComparisonChart({
  ruleMetrics,
  mlMetrics,
}: {
  ruleMetrics: Record<string, unknown>;
  mlMetrics: Record<string, unknown>;
}) {
  const keys = ["accuracy", "precision", "recall", "f1"];
  const data = keys
    .filter((k) => typeof ruleMetrics[k] === "number" || typeof mlMetrics[k] === "number")
    .map((k) => ({
      metric: k,
      "Rule-based": typeof ruleMetrics[k] === "number" ? (ruleMetrics[k] as number) : null,
      "ML model": typeof mlMetrics[k] === "number" ? (mlMetrics[k] as number) : null,
    }));

  return (
    <div className="h-56 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border)" />
          <XAxis dataKey="metric" tick={{ fontSize: 12 }} axisLine={false} tickLine={false} />
          <YAxis domain={[0, 1]} tick={{ fontSize: 12 }} axisLine={false} tickLine={false} width={32} />
          <Tooltip contentStyle={{ fontSize: 12, borderRadius: 6 }} />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Bar dataKey="Rule-based" fill="#71717a" radius={[4, 4, 0, 0]} />
          <Bar dataKey="ML model" fill="#6d28d9" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}