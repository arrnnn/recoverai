import { Target, Crosshair, Activity, Gauge, LineChart } from "lucide-react";
import { api, type ModelPerformance, type RecoveryPerformance } from "@/lib/api";
import { KpiCard } from "@/components/kpi-card";
import { MetricsComparisonChart } from "@/components/metrics-comparison-chart";
import { RevenueBreakdownChart } from "@/components/revenue-breakdown-chart";
import { MiniStatusChart } from "@/components/mini-status-chart";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

function fmtPct(v: unknown): string {
  return typeof v === "number" ? `${(v * 100).toFixed(1)}%` : "—";
}
function fmtUsd(v: unknown): string {
  return typeof v === "number" ? `$${v.toLocaleString(undefined, { maximumFractionDigits: 0 })}` : "—";
}

export default async function AnalyticsPage() {
  let modelPerf: ModelPerformance | null = null;
  let recoveryPerf: RecoveryPerformance | null = null;
  let error: string | null = null;

  try {
    [modelPerf, recoveryPerf] = await Promise.all([api.getModelPerformance(), api.getRecoveryPerformance()]);
  } catch {
    error =
      "Could not reach the RecoverAI API. Make sure the backend is running at " +
      (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000") +
      ".";
  }

  if (error || !modelPerf || !recoveryPerf) {
    return (
      <Card>
        <CardContent className="py-10 text-center text-sm text-muted-foreground">{error}</CardContent>
      </Card>
    );
  }

  const m = modelPerf.test_metrics;
  const ruleBased = recoveryPerf.rule_based as { metrics?: Record<string, unknown>; business?: Record<string, unknown> } | null;
  const mlModel = recoveryPerf.ml_model as { metrics?: Record<string, unknown>; business?: Record<string, unknown> } | null;

  let insight: string | null = null;
  if (ruleBased?.business && mlModel?.business) {
    const ruleMissed = ruleBased.business.missed_recoverable_value as number;
    const mlMissed = mlModel.business.missed_recoverable_value as number;
    const ruleWasted = ruleBased.business.wasted_effort_value as number;
    const mlWasted = mlModel.business.wasted_effort_value as number;
    if ([ruleMissed, mlMissed, ruleWasted, mlWasted].every((v) => typeof v === "number")) {
      const missedDelta = ruleMissed - mlMissed;
      const wastedDelta = mlWasted - ruleWasted;
      insight = `The ML model recovers ${fmtUsd(Math.abs(missedDelta))} ${missedDelta >= 0 ? "more" : "less"} in previously-missed revenue than the rule-based baseline, while spending ${fmtUsd(Math.abs(wastedDelta))} ${wastedDelta >= 0 ? "more" : "less"} on unrecoverable cases. Both numbers are measured on the same held-out test set.`;
    }
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Analytics</h1>
        <p className="text-sm text-muted-foreground">
          Measured model performance ({modelPerf.model_selected}) and rule-based vs. ML recovery comparison.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
        <KpiCard icon={Target} label="Accuracy" value={fmtPct(m.accuracy)} />
        <KpiCard icon={Crosshair} label="Precision" value={fmtPct(m.precision)} />
        <KpiCard icon={Activity} label="Recall" value={fmtPct(m.recall)} />
        <KpiCard icon={Gauge} label="F1 score" value={fmtPct(m.f1)} />
        <KpiCard icon={LineChart} label="ROC-AUC" value={typeof m.roc_auc === "number" ? m.roc_auc.toFixed(3) : "—"} tone="info" />
      </div>

      {insight && (
        <Card className="border-info-border bg-info-soft">
          <CardContent className="py-3 text-sm text-info">{insight}</CardContent>
        </Card>
      )}

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Rule-based vs. ML model</CardTitle>
            <CardDescription>Same held-out test set for both approaches.</CardDescription>
          </CardHeader>
          <CardContent>
            {ruleBased?.metrics && mlModel?.metrics ? (
              <MetricsComparisonChart ruleMetrics={ruleBased.metrics} mlMetrics={mlModel.metrics} />
            ) : (
              <p className="py-10 text-center text-sm text-muted-foreground">
                Run <code>python ml/rule_baseline.py</code> to generate this comparison.
              </p>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Recovery outcomes</CardTitle>
            <CardDescription>Live counts from every case the agent has processed.</CardDescription>
          </CardHeader>
          <CardContent>
            <MiniStatusChart data={recoveryPerf.by_recovery_status} />
          </CardContent>
        </Card>
      </div>

      {ruleBased?.business && mlModel?.business && (
        <Card>
          <CardHeader>
            <CardTitle>Revenue correctly identified vs. missed vs. wasted</CardTitle>
            <CardDescription>Dollar impact of each approach's classification errors.</CardDescription>
          </CardHeader>
          <CardContent>
            <RevenueBreakdownChart ruleBusiness={ruleBased.business} mlBusiness={mlModel.business} />
          </CardContent>
        </Card>
      )}
    </div>
  );
}