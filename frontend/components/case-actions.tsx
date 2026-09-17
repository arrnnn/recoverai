"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { api, ApiError } from "@/lib/api";
import { Loader2 } from "lucide-react";

export function CaseActions({ caseId, status }: { caseId: string; status: string }) {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);
  const [pendingAction, setPendingAction] = useState<"analyze" | "recover" | null>(null);

  function runAnalyze() {
    setError(null);
    setPendingAction("analyze");
    startTransition(async () => {
      try {
        await api.analyzeCase(caseId);
        router.refresh();
      } catch (e) {
        setError(e instanceof ApiError ? e.message : "Analyze failed unexpectedly.");
      } finally {
        setPendingAction(null);
      }
    });
  }

  function runRecover() {
    setError(null);
    setPendingAction("recover");
    startTransition(async () => {
      try {
        await api.recoverCase(caseId);
        router.refresh();
      } catch (e) {
        setError(e instanceof ApiError ? e.message : "Recover failed unexpectedly.");
      } finally {
        setPendingAction(null);
      }
    });
  }

  return (
    <div className="space-y-1.5">
      <div className="flex gap-2">
        <Button onClick={runAnalyze} disabled={isPending || status !== "NEW"} size="sm">
          {isPending && pendingAction === "analyze" && <Loader2 className="animate-spin" />}
          Analyze
        </Button>
        <Button onClick={runRecover} disabled={isPending || status !== "ANALYZED"} variant="secondary" size="sm">
          {isPending && pendingAction === "recover" && <Loader2 className="animate-spin" />}
          Recover (Simulated)
        </Button>
      </div>
      <p className="text-[11px] text-muted-foreground">
        {status === "RESOLVED" ? "This case has already been resolved." : "No real payments are processed by these actions."}
      </p>
      {error && <p className="text-xs text-danger">{error}</p>}
    </div>
  );
}