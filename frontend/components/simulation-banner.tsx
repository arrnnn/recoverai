import { Info } from "lucide-react";

export function SimulationBanner() {
  return (
    <div className="flex items-center gap-2 rounded-md border border-info-border bg-info-soft px-3 py-2 text-xs text-info">
      <Info className="size-3.5 shrink-0" />
      <span>
        <span className="font-semibold">Simulation mode.</span> Every recovery action here is simulated —
        no real payments are charged and no real emails are sent.
      </span>
    </div>
  );
}