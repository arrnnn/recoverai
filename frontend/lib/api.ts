/**
 * RecoverAI - API Client
 * ========================
 * Thin typed wrapper around fetch() for talking to the FastAPI backend.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
    cache: "no-store",
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, body.detail || "Request failed");
  }
  return res.json();
}

export interface CaseSummary {
  case_id: string;
  case_type: string;
  transaction_amount: number;
  failure_reason: string;
  status: string;
  created_at: string;
  risk_level: string | null;
  latest_action: string | null;
}

export interface CaseDetail extends CaseSummary {
  checkout_value: number;
  payment_method: string;
  gateway: string;
  failure_frequency: number;
  previous_recovery_attempts: number;
  previous_recovery_success_rate: number;
  customer_id: string | null;
  customer_segment: string | null;
  latest_prediction: {
    recoverable_probability: number;
    risk_level: string;
    model_name: string;
  } | null;
  latest_recovery_action: {
    root_cause: string;
    recommended_action: string;
    final_action: string;
    policy_decision: string;
    policy_rule: string | null;
    recovery_status: string;
    recovered_amount: number;
  } | null;
}

export interface AnalyzeResult {
  case_id: string;
  recoverable_probability: number;
  risk_level: string;
  root_cause: string;
  llm_recommended_action: string;
  llm_confidence: number;
  policy_decision: string;
  policy_rule: string | null;
  policy_reason: string;
  final_action: string;
}

export interface RecoverResult {
  case_id: string;
  final_action: string;
  recovery_status: string;
  recovered_amount_usd: number;
  recovered_amount_display: string;
}

export interface AnalyticsSummary {
  total_cases: number;
  revenue_at_risk_usd: number;
  revenue_recovered_usd: number;
  recovery_rate: number;
  high_risk_cases: number;
  successful_recoveries: number;
  escalated_cases: number;
}

export interface ModelPerformance {
  model_selected: string;
  test_metrics: Record<string, unknown>;
  candidate_comparison: Record<string, unknown>;
}

export interface RecoveryPerformance {
  rule_based: Record<string, unknown> | null;
  ml_model: Record<string, unknown> | null;
  by_action_type: Record<string, number>;
  by_recovery_status: Record<string, number>;
}

export interface AgentRunEntry {
  node: string;
  message: string;
  timestamp: string;
  [key: string]: unknown;
}

export interface AgentRun {
  case_id: string;
  status: string;
  execution_log: AgentRunEntry[];
  final_response: Record<string, unknown>;
  started_at: string;
  completed_at: string;
}

export interface PolicyRule {
  rule_name: string;
  description: string;
  threshold_value: string | null;
  active: boolean;
}

export const api = {
  health: () => request<{ status: string }>("/health"),

  listCases: (params?: { status?: string; limit?: number; offset?: number }) => {
    const qs = new URLSearchParams();
    if (params?.status) qs.set("status", params.status);
    if (params?.limit) qs.set("limit", String(params.limit));
    if (params?.offset) qs.set("offset", String(params.offset));
    const suffix = qs.toString() ? `?${qs.toString()}` : "";
    return request<CaseSummary[]>(`/cases${suffix}`);
  },

  getCase: (caseId: string) => request<CaseDetail>(`/cases/${caseId}`),

  createCase: (payload: Record<string, unknown>) =>
    request<CaseSummary>("/cases", { method: "POST", body: JSON.stringify(payload) }),

  analyzeCase: (caseId: string) =>
    request<AnalyzeResult>(`/cases/${caseId}/analyze`, { method: "POST" }),

  recoverCase: (caseId: string) =>
    request<RecoverResult>(`/cases/${caseId}/recover`, { method: "POST" }),

  getSummary: () => request<AnalyticsSummary>("/analytics/summary"),

  getModelPerformance: () => request<ModelPerformance>("/analytics/model-performance"),

  getRecoveryPerformance: () => request<RecoveryPerformance>("/analytics/recovery-performance"),

  getAgentRuns: (caseId: string) => request<AgentRun[]>(`/agent/runs/${caseId}`),

  getPolicies: () => request<PolicyRule[]>("/policies"),
};