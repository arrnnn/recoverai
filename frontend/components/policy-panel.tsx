import { ShieldCheck, ShieldAlert, ShieldX } from "lucide-react";
import { cn } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { StatusBadge } from "@/components/status-badge";
import type { PolicyRule } from "@/lib/api";

export function PolicyPanel({
  rules,
  triggeredRule,
  decision,
  recommendedAction,
  finalAction,
}: {
  rules: PolicyRule[];
  triggeredRule: string | null;
  decision: string;
  recommendedAction: string;
  finalAction: string;
}) {
  const DecisionIcon = decision === "APPROVED" ? ShieldCheck : decision === "REJECTED" ? ShieldX : ShieldAlert;

  return (
    <Card className="border-info-border">
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <div>
          <CardTitle className="flex items-center gap-2">
            <DecisionIcon className="size-4 text-info" />
            Policy Engine
          </CardTitle>
          <CardDescription>Deterministic rules — the LLM recommends, this decides.</CardDescription>
        </div>
        <StatusBadge value={decision} />
      </CardHeader>
      <CardContent className="space-y-3">
        {recommendedAction !== finalAction && (
          <div className="rounded-md border border-warning-border bg-warning-soft px-3 py-2 text-xs text-warning">
            AI recommended <span className="font-semibold">{recommendedAction}</span>, policy changed it to{" "}
            <span className="font-semibold">{finalAction}</span>.
          </div>
        )}
        <div className="space-y-1.5">
          {rules.map((rule) => {
            const isTriggered = rule.rule_name === triggeredRule;
            return (
              <div
                key={rule.rule_name}
                className={cn(
                  "flex items-start justify-between gap-3 rounded-md border px-3 py-2 text-xs",
                  isTriggered ? "border-info-border bg-info-soft" : "border-border"
                )}
              >
                <div>
                  <p className={cn("font-semibold", isTriggered && "text-info")}>
                    {rule.rule_name.replace(/_/g, " ")}
                  </p>
                  <p className="mt-0.5 text-muted-foreground">{rule.description}</p>
                </div>
                {isTriggered ? (
                  <span className="shrink-0 rounded-md bg-info px-2 py-0.5 font-semibold text-white">
                    Triggered
                  </span>
                ) : (
                  <span className="shrink-0 text-muted-foreground">passed</span>
                )}
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}