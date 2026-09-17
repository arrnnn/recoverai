"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Plus, Loader2 } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

const CASE_TYPES = ["failed_payment", "abandoned_checkout", "failed_subscription", "overdue_invoice"];
const PAYMENT_METHODS = ["credit_card", "debit_card", "paypal", "bank_transfer", "digital_wallet"];
const GATEWAYS = ["stripe", "adyen", "braintree", "paypal_gateway", "worldpay"];
const FAILURE_REASONS = [
  "insufficient_funds",
  "card_expired",
  "card_declined_generic",
  "bank_processing_error",
  "fraud_flag",
  "network_timeout",
  "incorrect_billing_details",
  "subscription_cancelled_by_bank",
  "invoice_disputed",
  "customer_unresponsive",
];
const SEGMENTS = ["enterprise", "smb", "consumer", "startup"];

type FormState = {
  case_type: string;
  transaction_amount: string;
  payment_method: string;
  gateway: string;
  failure_reason: string;
  failure_frequency: string;
  previous_recovery_attempts: string;
  previous_recovery_success_rate: string;
  customer_segment: string;
  customer_tenure_months: string;
};

const DEFAULT_FORM: FormState = {
  case_type: "failed_payment",
  transaction_amount: "120",
  payment_method: "credit_card",
  gateway: "stripe",
  failure_reason: "card_expired",
  failure_frequency: "0.05",
  previous_recovery_attempts: "0",
  previous_recovery_success_rate: "0.85",
  customer_segment: "consumer",
  customer_tenure_months: "24",
};

const PRESETS: { label: string; description: string; values: Partial<FormState> }[] = [
  {
    label: "Low-risk case",
    description: "Expired card, loyal customer -- should sail through as an easy retry.",
    values: {
      case_type: "failed_payment",
      transaction_amount: "120",
      failure_reason: "card_expired",
      customer_segment: "consumer",
      customer_tenure_months: "36",
      failure_frequency: "0.03",
      previous_recovery_attempts: "0",
      previous_recovery_success_rate: "0.9",
    },
  },
  {
    label: "High-value case",
    description: "$45,000 -- watch the policy engine override the AI regardless of confidence.",
    values: {
      case_type: "overdue_invoice",
      transaction_amount: "45000",
      failure_reason: "card_expired",
      payment_method: "credit_card",
      customer_segment: "enterprise",
      customer_tenure_months: "60",
      failure_frequency: "0.02",
      previous_recovery_attempts: "0",
      previous_recovery_success_rate: "0.95",
    },
  },
  {
    label: "Fraud case",
    description: "Flagged reason -- always escalated to a human, never auto-retried.",
    values: {
      case_type: "failed_subscription",
      transaction_amount: "50",
      failure_reason: "fraud_flag",
      customer_segment: "startup",
      customer_tenure_months: "2",
      failure_frequency: "0.5",
      previous_recovery_attempts: "1",
      previous_recovery_success_rate: "0.3",
    },
  },
];

export function NewCaseDialog() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState<FormState>(DEFAULT_FORM);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function applyPreset(values: Partial<FormState>) {
    setForm((f) => ({ ...f, ...values }));
  }

  function update<K extends keyof FormState>(key: K, value: string) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const amount = parseFloat(form.transaction_amount);
      const result = await api.createCase({
        case_type: form.case_type,
        transaction_amount: amount,
        checkout_value: amount,
        payment_method: form.payment_method,
        gateway: form.gateway,
        failure_reason: form.failure_reason,
        failure_frequency: parseFloat(form.failure_frequency),
        previous_recovery_attempts: parseInt(form.previous_recovery_attempts, 10),
        previous_recovery_success_rate: parseFloat(form.previous_recovery_success_rate),
        customer_id: `CUST-DEMO-${Date.now()}`,
        customer_segment: form.customer_segment,
        customer_tenure_months: parseFloat(form.customer_tenure_months),
      });
      setOpen(false);
      setForm(DEFAULT_FORM);
      router.push(`/cases/${result.case_id}`);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not create the case. Is the backend running?");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button size="sm">
          <Plus className="size-4" />
          New case
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create a new case</DialogTitle>
          <DialogDescription>
            Simulated only -- creating a case never touches real payments or sends real emails.
          </DialogDescription>
        </DialogHeader>

        <div className="grid grid-cols-3 gap-2">
          {PRESETS.map((preset) => (
            <button
              key={preset.label}
              type="button"
              onClick={() => applyPreset(preset.values)}
              className="rounded-md border border-border p-2 text-left text-xs hover:bg-accent"
              title={preset.description}
            >
              <p className="font-semibold">{preset.label}</p>
              <p className="mt-0.5 text-muted-foreground">{preset.description}</p>
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <Field label="Case type">
              <Select value={form.case_type} onChange={(v) => update("case_type", v)} options={CASE_TYPES} />
            </Field>
            <Field label="Failure reason">
              <Select value={form.failure_reason} onChange={(v) => update("failure_reason", v)} options={FAILURE_REASONS} />
            </Field>
            <Field label="Transaction amount (USD)">
              <input
                type="number"
                step="0.01"
                min="0"
                required
                value={form.transaction_amount}
                onChange={(e) => update("transaction_amount", e.target.value)}
                className="h-9 w-full rounded-md border border-border bg-background px-2.5 text-sm outline-none focus:ring-2 focus:ring-ring"
              />
            </Field>
            <Field label="Payment method">
              <Select value={form.payment_method} onChange={(v) => update("payment_method", v)} options={PAYMENT_METHODS} />
            </Field>
            <Field label="Gateway">
              <Select value={form.gateway} onChange={(v) => update("gateway", v)} options={GATEWAYS} />
            </Field>
            <Field label="Customer segment">
              <Select value={form.customer_segment} onChange={(v) => update("customer_segment", v)} options={SEGMENTS} />
            </Field>
            <Field label="Customer tenure (months)">
              <input
                type="number"
                min="0"
                value={form.customer_tenure_months}
                onChange={(e) => update("customer_tenure_months", e.target.value)}
                className="h-9 w-full rounded-md border border-border bg-background px-2.5 text-sm outline-none focus:ring-2 focus:ring-ring"
              />
            </Field>
            <Field label="Prior recovery attempts">
              <input
                type="number"
                min="0"
                value={form.previous_recovery_attempts}
                onChange={(e) => update("previous_recovery_attempts", e.target.value)}
                className="h-9 w-full rounded-md border border-border bg-background px-2.5 text-sm outline-none focus:ring-2 focus:ring-ring"
              />
            </Field>
            <Field label="Failure frequency (0-1)">
              <input
                type="number"
                step="0.01"
                min="0"
                max="1"
                value={form.failure_frequency}
                onChange={(e) => update("failure_frequency", e.target.value)}
                className="h-9 w-full rounded-md border border-border bg-background px-2.5 text-sm outline-none focus:ring-2 focus:ring-ring"
              />
            </Field>
            <Field label="Prior success rate (0-1)">
              <input
                type="number"
                step="0.01"
                min="0"
                max="1"
                value={form.previous_recovery_success_rate}
                onChange={(e) => update("previous_recovery_success_rate", e.target.value)}
                className="h-9 w-full rounded-md border border-border bg-background px-2.5 text-sm outline-none focus:ring-2 focus:ring-ring"
              />
            </Field>
          </div>

          {error && <p className="text-xs text-danger">{error}</p>}

          <DialogFooter>
            <Button type="submit" disabled={submitting}>
              {submitting && <Loader2 className="animate-spin" />}
              Create case
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block space-y-1">
      <span className="text-xs font-medium text-muted-foreground">{label}</span>
      {children}
    </label>
  );
}

function Select({ value, onChange, options }: { value: string; onChange: (v: string) => void; options: string[] }) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="h-9 w-full rounded-md border border-border bg-background px-2.5 text-sm outline-none focus:ring-2 focus:ring-ring"
    >
      {options.map((opt) => (
        <option key={opt} value={opt}>
          {opt}
        </option>
      ))}
    </select>
  );
}