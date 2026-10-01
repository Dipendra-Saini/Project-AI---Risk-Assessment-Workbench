import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import { Card, Spinner } from "../components/ui";

interface TokenResp {
  rows: { node: string; provider: string; model: string; status: string; calls: number; input_tokens: number; output_tokens: number; estimated_tokens: number }[];
  per_case: { cr_id: number; tokens: number }[];
  budget_per_case: number;
  mode: string;
}

export default function Tokens() {
  const q = useQuery({ queryKey: ["tokens"], queryFn: () => api<TokenResp>("/ops/tokens"), refetchInterval: 10000 });
  if (!q.data) return <Spinner label="loading usage" />;
  const d = q.data;
  const total = d.rows.reduce((a, r) => a + r.input_tokens + r.output_tokens, 0);
  const calls = d.rows.reduce((a, r) => a + r.calls, 0);
  const fallbacks = d.rows.filter((r) => r.status === "fallback").reduce((a, r) => a + r.calls, 0);
  const avoided = d.rows.filter((r) => r.status !== "ok" || r.provider === "offline").reduce((a, r) => a + r.estimated_tokens, 0);
  const max = Math.max(1, ...d.per_case.map((p) => p.tokens));

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold">AI usage and token budget</h1>
        <p className="text-sm text-slate-500">
          LLM mode <b>{d.mode}</b>. Per-case budget {d.budget_per_case.toLocaleString()} tokens; past the budget the pipeline switches to the deterministic fallback instead of failing.
          Free tiers only (Gemini Flash, Groq Llama), so the cost is $0. Tokens are tracked to stay inside rate limits.
        </p>
      </div>
      <div className="grid gap-4 md:grid-cols-4">
        {[
          ["Tokens used", total.toLocaleString()],
          ["LLM calls (incl. cache, fallback)", calls],
          ["Deterministic fallbacks", fallbacks],
          ["Tokens avoided (cache + fallback, estimated)", avoided.toLocaleString()],
        ].map(([k, v]) => (
          <Card key={k}>
            <p className="label">{k}</p>
            <p className="text-2xl font-semibold" data-testid={`metric-${k}`}>
              {v}
            </p>
          </Card>
        ))}
      </div>
      <Card title="By graph node and provider">
        <table className="w-full text-sm" data-testid="token-table">
          <thead className="text-left text-xs text-slate-500">
            <tr>
              <th>Node</th>
              <th>Provider / model</th>
              <th>Status</th>
              <th className="text-right">Calls</th>
              <th className="text-right">In</th>
              <th className="text-right">Out</th>
              <th className="text-right">Estimated</th>
            </tr>
          </thead>
          <tbody>
            {d.rows.map((r, i) => (
              <tr key={i} className="border-t border-slate-100">
                <td className="py-1 font-mono text-xs">{r.node}</td>
                <td className="text-xs">
                  {r.provider} / {r.model}
                </td>
                <td className="text-xs">{r.status}</td>
                <td className="text-right font-mono">{r.calls}</td>
                <td className="text-right font-mono">{r.input_tokens}</td>
                <td className="text-right font-mono">{r.output_tokens}</td>
                <td className="text-right font-mono text-slate-400">{r.estimated_tokens}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
      <Card title="Tokens per case vs budget">
        <ul className="space-y-1">
          {d.per_case.map((p) => (
            <li key={p.cr_id} className="flex items-center gap-2 text-xs">
              <span className="w-16 font-mono">case {p.cr_id}</span>
              <span className="h-3 rounded bg-indigo-500" style={{ width: `${(p.tokens / Math.max(max, d.budget_per_case)) * 70}%` }} />
              <span className="font-mono">{p.tokens}</span>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
