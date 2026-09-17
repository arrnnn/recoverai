"use client";

import { Bar, BarChart, ResponsiveContainer, Cell, XAxis, Tooltip } from "recharts";

const COLORS: Record<string, string> = {
  SUCCESS: "#15803d",
  FAILED: "#b91c1c",
  ESCALATED: "#6d28d9",
  BLOCKED: "#b45309",
};

export function MiniStatusChart({ data }: { data: Record<string, number> }) {
  const chartData = Object.entries(data).map(([status, count]) => ({ status, count }));

  if (chartData.length === 0) {
    return <div className="flex h-40 items-center justify-center text-xs text-muted-foreground">No recovery outcomes yet</div>;
  }

  return (
    <div className="h-40 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={chartData} barCategoryGap="25%">
          <XAxis dataKey="status" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
          <Tooltip contentStyle={{ fontSize: 12, borderRadius: 6 }} />
          <Bar dataKey="count" radius={[4, 4, 0, 0]}>
            {chartData.map((entry, i) => (
              <Cell key={i} fill={COLORS[entry.status] || "#71717a"} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}