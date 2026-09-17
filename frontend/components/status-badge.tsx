import { cn } from "@/lib/utils";

/**
 * Semantic status coloring used consistently everywhere in the app:
 *   green   = success / approved / low risk
 *   red     = failed / rejected / blocked / high risk
 *   amber   = pending / new / medium risk / warning
 *   violet  = escalated / AI-ML related
 */
const STATUS_CLASSES: Record<string, string> = {
  SUCCESS: "bg-success-soft text-success border-success-border",
  RESOLVED: "bg-success-soft text-success border-success-border",
  APPROVED: "bg-success-soft text-success border-success-border",
  low: "bg-success-soft text-success border-success-border",

  NEW: "bg-warning-soft text-warning border-warning-border",
  ANALYZED: "bg-warning-soft text-warning border-warning-border",
  PENDING: "bg-warning-soft text-warning border-warning-border",
  medium: "bg-warning-soft text-warning border-warning-border",

  FAILED: "bg-danger-soft text-danger border-danger-border",
  REJECTED: "bg-danger-soft text-danger border-danger-border",
  BLOCKED: "bg-danger-soft text-danger border-danger-border",
  high: "bg-danger-soft text-danger border-danger-border",

  ESCALATED: "bg-info-soft text-info border-info-border",
  "N/A": "bg-muted text-muted-foreground border-border",
};

export function StatusBadge({ value }: { value: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium",
        STATUS_CLASSES[value] || "bg-muted text-muted-foreground border-border"
      )}
    >
      {value}
    </span>
  );
}