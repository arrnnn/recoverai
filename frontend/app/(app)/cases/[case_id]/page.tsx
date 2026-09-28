import { notFound } from "next/navigation";
import { Brain, Lightbulb } from "lucide-react";
import { api, ApiError, type AgentRun, type PolicyRule } from "@/lib/api";
import { formatDual } from "@/lib/currency";
import { StatusBadge } from "@/components/status-badge";
import { CaseActions } from "@/components/case-actions";
import { PolicyPanel } from "@/components/policy-panel";
import { WorkflowTimeline } from "@/components/workflow-timeline";
import { SimulationBanner } from "@/components/simulation-banner";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";

export default async function CaseDetailPage({ params }: { params: Promise<{ case_id: string }> }) {
  const { case_id } = await params;

  let caseDetail;
  let agentRuns: AgentRun[] = [];
  let policies: PolicyRule[] = [];
  let loadError: string | null = null;

  try {
    caseDetail = await api.getCase(case_id);
    [agentRuns, policies] = await Promise.all([
      api.getAgentRuns(case_id).catch(() => []),
      api.getPolicies().catch(() => []),
    ]);
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) notFound();
    loadError =
      "Could not reach the RecoverAI API. Make sure the backend is running at " +
      (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000") +
      ".";
  }

  if (loadError || !caseDetail) {
    return (
      <Card>
        <CardContent className="py-10 text-center text-sm text-muted-foreground">{loadError}</CardContent>
      </Card>
    );
  }

  const { latest_prediction, latest_recovery_action } = caseDetail;
  const latestRun = agentRuns[agentRuns.length - 1];

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-xl font-semibold tracking-tight">{caseDetail.case_id}</h1>
            <StatusBadge value={caseDetail.status} />
          </div>
          <p className="text-sm text-muted-foreground">
            {caseDetail.case_type} · {caseDetail.failure_reason} · created{" "}
            {new Date(caseDetail.created_at).toLocaleString()}
          </p>
        </div>
        <CaseActions caseId={caseDetail.case_id} status={caseDetail.status} />
      </div>

      <SimulationBanner />

      {latestRun && (
        <Card>
          <CardHeader>
            <CardTitle>Agent workflow</CardTitle>
            <CardDescription>The 8-step LangGraph execution for this case. Click a step for detail.</CardDescription>
          </CardHeader>
          <CardContent>
            <WorkflowTimeline entries={latestRun.execution_log} />
          </CardContent>
        </Card>
      )}

      <div className="grid gap-4 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>Case details</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2.5 text-sm">
            <Row label="Transaction amount" value={formatDual(caseDetail.transaction_amount)} />
            <Row label="Payment method" value={caseDetail.payment_method} />
            <Row label="Gateway" value={caseDetail.gateway} />
            <Row label="Failure frequency" value={`${(caseDetail.failure_frequency * 100).toFixed(0)}%`} />
            <Row label="Prior recovery attempts" value={String(caseDetail.previous_recovery_attempts)} />
            <Row label="Prior success rate" value={`${(caseDetail.previous_recovery_success_rate * 100).toFixed(0)}%`} />
            <Separator />
            <Row label="Customer" value={caseDetail.customer_id || "—"} />
            <Row label="Segment" value={caseDetail.customer_segment || "—"} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-1.5">
              <Brain className="size-3.5 text-info" /> ML prediction
            </CardTitle>
            <CardDescription>Recoverability estimate from the trained model.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2.5 text-sm">
            {latest_prediction ? (
              <>
                <Row label="Recoverable probability" value={`${(latest_prediction.recoverable_probability * 100).toFixed(1)}%`} />
                <Row label="Risk level" value={<StatusBadge value={latest_prediction.risk_level} />} />
                <Row label="Model" value={latest_prediction.model_name} />
              </>
            ) : (
              <p className="text-muted-foreground">Not analyzed yet. Click Analyze to run the model.</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-1.5">
              <Lightbulb className="size-3.5 text-info" /> AI recommendation
            </CardTitle>
            <CardDescription>LLM root-cause analysis and recommended action.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-2.5 text-sm">
            {latest_recovery_action ? (
              <>
                <Row label="Root cause" value={latest_recovery_action.root_cause || "—"} />
                <Row label="Recommended action" value={latest_recovery_action.recommended_action} />
                <Separator />
                <Row label="Recovery status" value={<StatusBadge value={latest_recovery_action.recovery_status} />} />
                <Row label="Recovered amount" value={formatDual(latest_recovery_action.recovered_amount)} />
              </>
            ) : (
              <p className="text-muted-foreground">No agent decision yet.</p>
            )}
          </CardContent>
        </Card>
      </div>

      {latest_recovery_action && policies.length > 0 && (
        <PolicyPanel
          rules={policies}
          triggeredRule={latest_recovery_action.policy_rule}
          decision={latest_recovery_action.policy_decision}
          recommendedAction={latest_recovery_action.recommended_action}
          finalAction={latest_recovery_action.final_action}
        />
      )}
    </div>
  );
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-4">
      <span className="text-muted-foreground">{label}</span>
      <span className="text-right font-medium">{value}</span>
    </div>
  );
}