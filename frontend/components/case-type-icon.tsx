import { CreditCard, ShoppingCart, RefreshCw, FileText, Receipt } from "lucide-react";
import { cn } from "@/lib/utils";

const CASE_TYPE_META: Record<string, { icon: typeof CreditCard; tone: string }> = {
  failed_payment: { icon: CreditCard, tone: "bg-blue text-blue-fg" },
  abandoned_checkout: { icon: ShoppingCart, tone: "bg-rose text-rose-fg" },
  failed_subscription: { icon: RefreshCw, tone: "bg-lavender text-lavender-fg" },
  overdue_invoice: { icon: FileText, tone: "bg-muted text-ink-soft" },
};

export function CaseTypeIcon({ caseType, className }: { caseType: string; className?: string }) {
  const meta = CASE_TYPE_META[caseType] || { icon: Receipt, tone: "bg-muted text-ink-soft" };
  const Icon = meta.icon;
  return (
    <span
      className={cn(
        "flex size-10 shrink-0 items-center justify-center rounded-2xl",
        meta.tone,
        className
      )}
    >
      <Icon className="size-4.5" />
    </span>
  );
}