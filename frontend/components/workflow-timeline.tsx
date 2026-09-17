import {
  FileSearch,
  Brain,
  Lightbulb,
  GitBranch,
  ShieldCheck,
  Zap,
  CheckCircle2,
  FileOutput,
  Circle,
} from "lucide-react";
import type { AgentRunEntry } from "@/lib/api";

const NODE_META: Record<string, { label: string; icon: React.ComponentType<{ className?: string }> }> = {
  analyze_case: { label: "Analyze Case", icon: FileSearch },
  ml_prediction: { label: "ML Prediction", icon: Brain },
  root_cause_analysis: { label: "Root Cause (AI)", icon: Lightbulb },
  decision_router: { label: "Decision Router", icon: GitBranch },
  policy_check: { label: "Policy Check", icon: ShieldCheck },
  recovery_action: { label: "Recovery Action", icon: Zap },
  record_outcome: { label: "Record Outcome", icon: CheckCircle2 },
  final_response: { label: "Final Response", icon: FileOutput },
};

export function WorkflowTimeline({ entries }: { entries: AgentRunEntry[] }) {
  return (
    <ol className="grid grid-cols-1 gap-0 sm:grid-cols-4 lg:grid-cols-8">
      {entries.map((entry, i) => {
        const meta = NODE_META[entry.node] || { label: entry.node, icon: Circle };
        const Icon = meta.icon;
        const isLast = i === entries.length - 1;
        return (
          <li key={i} className="relative flex sm:flex-col">
            <div className="flex flex-col items-center sm:w-full">
              <div className="flex items-center sm:w-full">
                <span className="flex size-7 shrink-0 items-center justify-center rounded-full border border-info-border bg-info-soft text-info">
                  <Icon className="size-3.5" />
                </span>
                {!isLast && (
                  <span className="hidden h-px flex-1 bg-border sm:block" />
                )}
              </div>
            </div>
            <div className="ml-3 flex-1 pb-4 sm:ml-0 sm:mt-2 sm:pb-0 sm:pr-2">
              <details className="group">
                <summary className="cursor-pointer list-none text-xs font-semibold">
                  {meta.label}
                </summary>
                <p className="mt-1 text-xs text-muted-foreground">{entry.message}</p>
              </details>
            </div>
          </li>
        );
      })}
    </ol>
  );
}