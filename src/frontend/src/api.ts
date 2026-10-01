export type Role = "product_owner" | "analyst" | "committee";

export interface User {
  id: number;
  username: string;
  name: string;
  role: Role;
}

export interface Field<T = unknown> {
  value: T;
  confidence: number;
  source_span: string;
  origin: string;
}

export interface Extraction {
  id: number;
  version: number;
  data: Record<string, Field>;
  flags: string[];
  provider: string;
  prompt_version: string;
  confirmed: boolean;
  confirmed_by: string | null;
}

export interface Factor {
  dimension: string;
  likelihood: number;
  impact: number;
  origin: "rule" | "ai" | "offline" | "human" | "pending";
  rule_ids: string[];
  risk_types: string[];
  rationale: string;
  citations: string[];
  confirmed: boolean;
  inherent: number;
  mitigation: number;
  residual: number;
  combined_effectiveness: number;
  floor_applied: boolean;
}

export interface AssessmentControl {
  control_id: string;
  name: string;
  dims: string[];
  design: number;
  operating: number;
  origin: string;
  matched_on: string;
}

export interface Claim {
  index: number;
  dimension: string;
  text: string;
  citations: string[];
  status: "ok" | "doubtful" | "unsupported";
  reason: string;
}

export interface Assessment {
  id: number;
  version: number;
  config_version_id: number;
  inherent: number;
  inherent_tier: string;
  residual: number;
  residual_tier: string;
  risk_types: string[];
  factors: Factor[];
  controls: AssessmentControl[];
  steps: string[];
  config_hash: string;
  retrieval: Record<string, { id: string; score: number }[]>;
  narrative: { summary: string; sections: { dimension: string; text: string }[]; suggested_conditions?: string[] } | null;
  narrative_provider: string;
  narrative_stale: boolean;
  critique: { claims: Claim[]; unsupported: number; checked_by: string } | null;
  narrative_signed_by: string | null;
  warnings_ack_reason: string | null;
}

export interface Gate {
  passed: boolean;
  label: string;
  blocking: string[];
}

export interface Override {
  id: number;
  target_type: string;
  target_key: string;
  old_value: unknown;
  new_value: unknown;
  reason: string;
  by: string;
  by_id: number;
  tier_before: string | null;
  tier_after: string | null;
  requires_ack: boolean;
  acked_by: string | null;
  created_at: string;
}

export interface CaseSummary {
  id: number;
  ref: string;
  title: string;
  change_type: string;
  business_line: string;
  status: string;
  pipeline_state: string;
  pipeline_step: string;
  needs_human: boolean;
  warnings: string[];
  created_by: string | null;
  created_at: string;
  updated_at: string;
  residual_tier: string | null;
  residual: number | null;
}

export interface CaseDetail extends CaseSummary {
  description: string;
  info_request: string | null;
  config_version_id: number | null;
  graph_run: number;
  waiting_at: string | null;
  documents: { id: number; filename: string; size: number; sha256: string; preview: string }[];
  extraction: Extraction | null;
  assessment: Assessment | null;
  gates: Record<"G0" | "G1" | "G1b" | "G2" | "G3", Gate>;
  overrides: Override[];
  committee_round: number;
  votes: { round: number; member: string; member_id: number; vote: string | null; conflict: boolean; rationale: string; conditions: string[] }[];
  decisions: { round: number; outcome: string; conditions: string[]; summary: Record<string, unknown>; recorded_by: string; at: string }[];
  ai_usage: { calls: number; input_tokens: number; output_tokens: number; cache_hits: number; fallbacks: number; by_node: Record<string, number> };
}

export interface Chunk {
  id: string;
  doc_title: string;
  section_title: string;
  text: string;
  tags: string[];
  source_url: string | null;
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

const TOKEN_KEY = "raw.token";
export const token = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (t: string) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

export async function api<T = unknown>(path: string, init: RequestInit & { json?: unknown } = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const t = token.get();
  if (t) headers.set("Authorization", `Bearer ${t}`);
  let body = init.body;
  if (init.json !== undefined) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(init.json);
  }
  const res = await fetch(`/api${path}`, { ...init, headers, body });
  if (res.status === 401 && path !== "/auth/login") {
    token.clear();
    window.location.assign("/login");
  }
  if (!res.ok) {
    let msg = res.statusText;
    try {
      const j = await res.json();
      msg = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail);
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, msg);
  }
  const type = res.headers.get("content-type") ?? "";
  return (type.includes("json") ? res.json() : res.text()) as Promise<T>;
}

export const post = <T = CaseDetail>(path: string, json: unknown = {}) => api<T>(path, { method: "POST", json });

export const DIM_NAMES: Record<string, string> = {
  PRD: "Products and services",
  CUS: "Customers and entities",
  GEO: "Geography",
  CHN: "Delivery channels",
  TRX: "Transactions",
  TPV: "Third parties and vendors",
};

export const ROLE_LABEL: Record<Role, string> = {
  product_owner: "Product owner",
  analyst: "FCRM analyst",
  committee: "Risk committee",
};
