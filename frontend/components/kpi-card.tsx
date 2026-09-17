import { cn } from "@/lib/utils";
import { Card } from "@/components/ui/card";

const TONE_CLASSES = {
  neutral: "bg-muted text-foreground",
  success: "bg-success-soft text-success",
  danger: "bg-danger-soft text-danger",
  warning: "bg-warning-soft text-warning",
  info: "bg-info-soft text-info",
} as const;

export function KpiCard({
  icon: Icon,
  label,
  value,
  sublabel,
  tone = "neutral",
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
  sublabel?: string;
  tone?: keyof typeof TONE_CLASSES;
}) {
  return (
    <Card className="gap-2 p-4">
      <div className="flex items-center gap-2">
        <span className={cn("flex size-7 items-center justify-center rounded-md", TONE_CLASSES[tone])}>
          <Icon className="size-3.5" />
        </span>
        <p className="text-xs font-medium text-muted-foreground">{label}</p>
      </div>
      <p className="tabular text-2xl font-semibold leading-none">{value}</p>
      {sublabel && <p className="text-xs text-muted-foreground">{sublabel}</p>}
    </Card>
  );
}