import Link from "next/link";
import { ArrowRight, AlertTriangle, TrendingUp, Percent, Layers, ShieldAlert, CheckCircle2 } from "lucide-react";
import { api, type AnalyticsSummary, type CaseSummary, type RecoveryPerformance } from "@/lib/api";
import { formatDual } from "@/lib/currency";
import { StatusBadge } from "@/components/status-badge";
import { KpiCard } from "@/components/kpi-card";
import { SimulationBanner } from "@/components/simulation-banner";
import { SystemHealth } from "@/components/system-health";
import { RevenueComparisonChart } from "@/components/revenue-chart";
import { MiniStatusChart } from "@/components/mini-status-chart";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";

type DashboardResult =
  | { ok: true; summary: AnalyticsSummary; recentCases: CaseSummary[]; recoveryPerf: RecoveryPerformance }
  | { ok: false; error: string };

async function getDashboardData(): Promise<DashboardResult> {
  try {
    const [summary, recentCases, recoveryPerf] = await Promise.all([
      api.getSummary(),
      api.listCases({ limit: 8 }),
      api.getRecoveryPerformance(),
    ]);
    return { ok: true, summary, recentCases, recoveryPerf };
  } catch {
    return {
      ok: false,
      error:
        "Could not reach the RecoverAI API. Make sure the backend is running at " +
        (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000") +
        ".",
    };
  }
}

export default async function DashboardPage() {
  const data = await getDashboardData();

  if (!data.ok) {
    return (
      <Card>
        <CardContent className="py-10 text-center text-sm text-muted-foreground">{data.error}</CardContent>
      </Card>
    );
  }

  const { summary, recentCases, recoveryPerf } = data;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Dashboard</h1>
          <p className="text-sm text-muted-foreground">Live revenue-recovery performance.</p>
        </div>
        <SystemHealth />
      </div>

      <SimulationBanner />

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-3 xl:grid-cols-6">
        <KpiCard icon={AlertTriangle} label="Revenue at risk" value={formatDual(summary.revenue_at_risk_usd)} tone="danger" />
        <KpiCard icon={TrendingUp} label="Revenue recovered" value={formatDual(summary.revenue_recovered_usd)} tone="success" />
        <KpiCard icon={Percent} label="Recovery rate" value={`${(summary.recovery_rate * 100).toFixed(1)}%`} tone="info" />
        <KpiCard icon={Layers} label="Total cases" value={summary.total_cases.toLocaleString()} />
        <KpiCard icon={ShieldAlert} label="High-risk cases" value={summary.high_risk_cases.toLocaleString()} tone="warning" />
        <KpiCard icon={CheckCircle2} label="Successful recoveries" value={summary.successful_recoveries.toLocaleString()} tone="success" />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Revenue: at risk vs. recovered</CardTitle>
            <CardDescription>USD, current totals across all cases.</CardDescription>
          </CardHeader>
          <CardContent>
            <RevenueComparisonChart atRisk={summary.revenue_at_risk_usd} recovered={summary.revenue_recovered_usd} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Recovery outcomes</CardTitle>
            <CardDescription>Live counts by simulated recovery status.</CardDescription>
          </CardHeader>
          <CardContent>
            <MiniStatusChart data={recoveryPerf.by_recovery_status} />
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="flex-row items-center justify-between space-y-0">
          <CardTitle>Recent cases</CardTitle>
          <Link href="/cases" className="flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground">
            View all <ArrowRight className="size-3.5" />
          </Link>
        </CardHeader>
        <CardContent>
          {recentCases.length === 0 ? (
            <p className="py-6 text-center text-sm text-muted-foreground">No cases yet.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Case</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Amount</TableHead>
                  <TableHead>Risk</TableHead>
                  <TableHead>Action</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {recentCases.map((c) => (
                  <TableRow key={c.case_id}>
                    <TableCell>
                      <Link href={`/cases/${c.case_id}`} className="font-medium hover:underline">
                        {c.case_id}
                      </Link>
                    </TableCell>
                    <TableCell className="text-muted-foreground">{c.case_type}</TableCell>
                    <TableCell className="tabular">{formatDual(c.transaction_amount)}</TableCell>
                    <TableCell>{c.risk_level ? <StatusBadge value={c.risk_level} /> : <span className="text-muted-foreground">—</span>}</TableCell>
                    <TableCell className="text-muted-foreground">{c.latest_action || "—"}</TableCell>
                    <TableCell><StatusBadge value={c.status} /></TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}