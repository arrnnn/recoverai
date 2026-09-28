"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Search, ArrowUpDown } from "lucide-react";
import { api, type CaseSummary } from "@/lib/api";
import { formatDual } from "@/lib/currency";
import { StatusBadge } from "@/components/status-badge";
import { NewCaseDialog } from "@/components/new-case-dialog";
import { Card, CardContent } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { cn } from "@/lib/utils";

type SortKey = "created_at" | "transaction_amount" | "case_id";

export default function CasesPage() {
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [typeFilter, setTypeFilter] = useState("ALL");
  const [riskFilter, setRiskFilter] = useState("ALL");
  const [actionFilter, setActionFilter] = useState("ALL");
  const [sortKey, setSortKey] = useState<SortKey>("created_at");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

  useEffect(() => {
    api
      .listCases({ limit: 200 })
      .then(setCases)
      .catch(() =>
        setError(
          "Could not reach the RecoverAI API. Make sure the backend is running at " +
            (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000") +
            "."
        )
      )
      .finally(() => setLoading(false));
  }, []);

  const caseTypes = useMemo(() => Array.from(new Set(cases.map((c) => c.case_type))), [cases]);
  const actions = useMemo(
    () => Array.from(new Set(cases.map((c) => c.latest_action).filter(Boolean))) as string[],
    [cases]
  );

  const filtered = useMemo(() => {
    let rows = cases;
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      rows = rows.filter(
        (c) => c.case_id.toLowerCase().includes(q) || c.failure_reason.toLowerCase().includes(q)
      );
    }
    if (statusFilter !== "ALL") rows = rows.filter((c) => c.status === statusFilter);
    if (typeFilter !== "ALL") rows = rows.filter((c) => c.case_type === typeFilter);
    if (riskFilter !== "ALL") rows = rows.filter((c) => c.risk_level === riskFilter);
    if (actionFilter !== "ALL") rows = rows.filter((c) => c.latest_action === actionFilter);

    const sorted = [...rows].sort((a, b) => {
      let cmp = 0;
      if (sortKey === "created_at") cmp = new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
      if (sortKey === "transaction_amount") cmp = a.transaction_amount - b.transaction_amount;
      if (sortKey === "case_id") cmp = a.case_id.localeCompare(b.case_id);
      return sortDir === "asc" ? cmp : -cmp;
    });
    return sorted;
  }, [cases, search, statusFilter, typeFilter, riskFilter, actionFilter, sortKey, sortDir]);

  function toggleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">Cases</h1>
          <p className="text-sm text-muted-foreground">Every revenue-recovery case the platform has ingested.</p>
        </div>
        <NewCaseDialog />
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search case ID or reason..."
            className="h-9 w-56 rounded-md border border-border bg-background pl-8 pr-3 text-sm outline-none focus:ring-2 focus:ring-ring"
          />
        </div>
        <Select value={statusFilter} onChange={setStatusFilter} label="Status" options={["ALL", "NEW", "ANALYZED", "RESOLVED"]} />
        <Select value={typeFilter} onChange={setTypeFilter} label="Type" options={["ALL", ...caseTypes]} />
        <Select value={riskFilter} onChange={setRiskFilter} label="Risk" options={["ALL", "low", "medium", "high"]} />
        <Select value={actionFilter} onChange={setActionFilter} label="Action" options={["ALL", ...actions]} />
      </div>

      <Card>
        <CardContent>
          {loading ? (
            <p className="py-10 text-center text-sm text-muted-foreground">Loading cases…</p>
          ) : error ? (
            <p className="py-10 text-center text-sm text-muted-foreground">{error}</p>
          ) : filtered.length === 0 ? (
            <p className="py-10 text-center text-sm text-muted-foreground">No cases match these filters.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <SortableHead label="Case" active={sortKey === "case_id"} dir={sortDir} onClick={() => toggleSort("case_id")} />
                  <TableHead>Type</TableHead>
                  <SortableHead label="Amount" active={sortKey === "transaction_amount"} dir={sortDir} onClick={() => toggleSort("transaction_amount")} />
                  <TableHead>Reason</TableHead>
                  <TableHead>Risk</TableHead>
                  <TableHead>Action</TableHead>
                  <SortableHead label="Created" active={sortKey === "created_at"} dir={sortDir} onClick={() => toggleSort("created_at")} />
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.map((c) => (
                  <TableRow key={c.case_id}>
                    <TableCell>
                      <Link href={`/cases/${c.case_id}`} className="font-medium hover:underline">
                        {c.case_id}
                      </Link>
                    </TableCell>
                    <TableCell className="text-muted-foreground">{c.case_type}</TableCell>
                    <TableCell className="tabular">{formatDual(c.transaction_amount)}</TableCell>
                    <TableCell className="text-muted-foreground">{c.failure_reason}</TableCell>
                    <TableCell>{c.risk_level ? <StatusBadge value={c.risk_level} /> : <span className="text-muted-foreground">—</span>}</TableCell>
                    <TableCell className="text-muted-foreground">{c.latest_action || "—"}</TableCell>
                    <TableCell className="text-muted-foreground">{new Date(c.created_at).toLocaleDateString()}</TableCell>
                    <TableCell><StatusBadge value={c.status} /></TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function Select({
  value,
  onChange,
  label,
  options,
}: {
  value: string;
  onChange: (v: string) => void;
  label: string;
  options: string[];
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="h-9 rounded-md border border-border bg-background px-2.5 text-sm text-foreground outline-none focus:ring-2 focus:ring-ring"
    >
      {options.map((opt) => (
        <option key={opt} value={opt}>
          {opt === "ALL" ? `All ${label.toLowerCase()}` : opt}
        </option>
      ))}
    </select>
  );
}

function SortableHead({
  label,
  active,
  dir,
  onClick,
}: {
  label: string;
  active: boolean;
  dir: "asc" | "desc";
  onClick: () => void;
}) {
  return (
    <TableHead>
      <button onClick={onClick} className={cn("flex items-center gap-1 hover:text-foreground", active && "text-foreground")}>
        {label}
        <ArrowUpDown className={cn("size-3", active && dir === "asc" && "rotate-180")} />
      </button>
    </TableHead>
  );
}