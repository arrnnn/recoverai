"use client";

import { Bar, BarChart, ResponsiveContainer, XAxis, YAxis, Tooltip, Legend, CartesianGrid } from "recharts";

export function RevenueBreakdownChart({
  ruleBusiness,
  mlBusiness,
}: {
  ruleBusiness: Record<string, unknown>;
  mlBusiness: Record<string, unknown>;
}) {
  const rows = [
    { key: "correctly_flagged_recoverable_value", label: "Correctly identified" },
    { key: "missed_recoverable_value", label: "Missed" },
    { key: "wasted_effort_value", label: "Wasted effort" },
  ];

  const data = rows.map((r) => ({
    outcome: r.label,
    "Rule-based": typeof ruleBusiness[r.key] === "number" ? (ruleBusiness[r.key] as number) : 0,
    "ML model": typeof mlBusiness[r.key] === "number" ? (mlBusiness[r.key] as number) : 0,
  }));

  return (
    <div className="h-56 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border)" />
          <XAxis dataKey="outcome" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
          <YAxis
            tick={{ fontSize: 11 }}
            axisLine={false}
            tickLine={false}
            width={56}
            tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`}
          />
          <Tooltip
            formatter={(value) => `$${Number(value).toLocaleString(undefined, { maximumFractionDigits: 0 })}`}
            contentStyle={{ fontSize: 12, borderRadius: 6 }}
          />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Bar dataKey="Rule-based" fill="#71717a" radius={[4, 4, 0, 0]} />
          <Bar dataKey="ML model" fill="#6d28d9" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}