"use client";

import { Bar, BarChart, ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid } from "recharts";

export function RevenueComparisonChart({ atRisk, recovered }: { atRisk: number; recovered: number }) {
  const data = [
    { name: "At risk", amount: atRisk },
    { name: "Recovered", amount: recovered },
  ];

  return (
    <div className="h-48 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} margin={{ top: 8, right: 8, left: 8, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border)" />
          <XAxis dataKey="name" tick={{ fontSize: 12 }} axisLine={false} tickLine={false} />
          <YAxis tick={{ fontSize: 12 }} axisLine={false} tickLine={false} width={60} />
          <Tooltip
            formatter={(value) => `$${Number(value).toLocaleString(undefined, { maximumFractionDigits: 2 })}`}
            contentStyle={{ fontSize: 12, borderRadius: 6 }}
          />
          <Bar dataKey="amount" radius={[4, 4, 0, 0]} fill="#6d28d9" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}