"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export function SystemHealth() {
  const [status, setStatus] = useState<"checking" | "online" | "offline">("checking");

  useEffect(() => {
    let cancelled = false;
    api
      .health()
      .then(() => !cancelled && setStatus("online"))
      .catch(() => !cancelled && setStatus("offline"));
    return () => {
      cancelled = true;
    };
  }, []);

  const dotClass =
    status === "online" ? "bg-success" : status === "offline" ? "bg-danger" : "bg-muted-foreground";
  const label = status === "online" ? "API online" : status === "offline" ? "API offline" : "Checking…";

  return (
    <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
      <span className={`size-1.5 rounded-full ${dotClass}`} />
      {label}
    </div>
  );
}