import Link from "next/link";
import { api, type AgentRun } from "@/lib/api";
import { StatusBadge } from "@/components/status-badge";
import { WorkflowTimeline } from "@/components/workflow-timeline";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface RunWithCase extends AgentRun {
  displayCaseId: string;
}

export default async function AgentActivityPage() {
  let runs: RunWithCase[] = [];
  let error: string | null = null;

  try {
    const recentCases = await api.listCases({ limit: 20 });
    const runsPerCase = await Promise.all(
      recentCases.map((c) =>
        api
          .getAgentRuns(c.case_id)
          .then((r) => r.map((run) => ({ ...run, displayCaseId: c.case_id })))
          .catch(() => [])
      )
    );
    runs = runsPerCase.flat().sort((a, b) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime());
  } catch {
    error =
      "Could not reach the RecoverAI API. Make sure the backend is running at " +
      (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000") +
      ".";
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">Agent Activity</h1>
        <p className="text-sm text-muted-foreground">Live feed of every agent run, most recent first.</p>
      </div>

      {error ? (
        <Card><CardContent className="py-10 text-center text-sm text-muted-foreground">{error}</CardContent></Card>
      ) : runs.length === 0 ? (
        <Card><CardContent className="py-10 text-center text-sm text-muted-foreground">No agent runs yet. Analyze a case to see activity here.</CardContent></Card>
      ) : (
        <div className="space-y-3">
          {runs.map((run, idx) => (
            <Card key={idx}>
              <CardHeader className="flex-row items-center justify-between space-y-0">
                <CardTitle>
                  <Link href={`/cases/${run.displayCaseId}`} className="hover:underline">
                    {run.displayCaseId}
                  </Link>
                </CardTitle>
                <div className="flex items-center gap-2">
                  <StatusBadge value={run.status} />
                  <span className="text-xs text-muted-foreground">{new Date(run.started_at).toLocaleString()}</span>
                </div>
              </CardHeader>
              <CardContent>
                <WorkflowTimeline entries={run.execution_log} />
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}