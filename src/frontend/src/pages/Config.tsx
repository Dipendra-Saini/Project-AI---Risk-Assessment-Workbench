import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { api, post } from "../api";
import { useAuth } from "../auth";
import { Button, Card, ErrorText, ReasonDialog, Spinner } from "../components/ui";

/* eslint-disable @typescript-eslint/no-explicit-any */
type Cfg = any;

interface ConfigResp {
  id: number;
  version: number;
  hash: string;
  note: string;
  created_by: string;
  created_at: string;
  content: Cfg;
}

function Num({ value, onChange, step = 0.05, disabled, testId }: { value: number; onChange: (v: number) => void; step?: number; disabled: boolean; testId?: string }) {
  return <input data-testid={testId} type="number" step={step} disabled={disabled} className="input w-28" value={value} onChange={(e) => onChange(Number(e.target.value))} />;
}

export default function Config() {
  const { user } = useAuth();
  const qc = useQueryClient();
  const editable = user?.role === "analyst";
  const active = useQuery({ queryKey: ["config"], queryFn: () => api<ConfigResp>("/config") });
  const history = useQuery({ queryKey: ["config-history"], queryFn: () => api<Omit<ConfigResp, "content">[]>("/config/history") });
  const [draft, setDraft] = useState<Cfg | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState<string | null>(null);
  useEffect(() => {
    if (active.data) setDraft(structuredClone(active.data.content));
  }, [active.data]);
  if (!active.data || !draft) return <Spinner label="loading config" />;
  const s = draft.scoring;
  const w = draft.workflow;
  const dirty = JSON.stringify(draft) !== JSON.stringify(active.data.content);
  const weightSum = Object.values(s.dimensions as Record<string, { weight: number }>).reduce((a, d) => a + d.weight, 0);
  const upd = (fn: (d: Cfg) => void) => {
    const d = structuredClone(draft);
    fn(d);
    setDraft(d);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Scoring and workflow configuration</h1>
          <p className="text-sm text-slate-500">
            Active version v{active.data.version} - hash {active.data.hash.slice(0, 12)}. Changes create a new immutable version and apply to new cases only.
            Run the golden-set evals on a candidate before activating it (evals/README.md).
          </p>
        </div>
        {editable && (
          <div className="flex gap-2">
            <Button variant="secondary" disabled={!dirty} onClick={() => setDraft(structuredClone(active.data!.content))}>
              Reset
            </Button>
            <Button data-testid="save-config" disabled={!dirty} onClick={() => setSaving(true)}>
              Save as new version
            </Button>
          </div>
        )}
      </div>
      {saved && <p className="rounded bg-emerald-50 px-3 py-2 text-sm text-emerald-800">{saved}</p>}

      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Dimension weights">
          <table className="w-full text-sm">
            <tbody>
              {Object.entries(s.dimensions as Record<string, { name: string; weight: number }>).map(([k, d]) => (
                <tr key={k} className="border-t border-slate-100">
                  <td className="py-1.5">
                    <span className="font-mono text-xs text-slate-500">{k}</span> {d.name}
                  </td>
                  <td className="text-right">
                    <Num testId={`weight-${k}`} disabled={!editable} value={d.weight} onChange={(v) => upd((x) => (x.scoring.dimensions[k].weight = v))} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className={`mt-2 text-xs ${Math.abs(weightSum - 1) > 1e-6 ? "font-semibold text-rose-700" : "text-slate-500"}`}>Sum of weights: {weightSum.toFixed(2)} (must be 1.00)</p>
        </Card>

        <Card title="Scoring method">
          <dl className="grid grid-cols-[1fr_auto] items-center gap-2 text-sm">
            <dt>Worst-dimension floor (overall &ge; ratio x worst)</dt>
            <dd>
              <Num disabled={!editable} value={s.max_dimension_floor_ratio} onChange={(v) => upd((x) => (x.scoring.max_dimension_floor_ratio = v))} />
            </dd>
            <dt>Mitigation cap (controls remove at most)</dt>
            <dd>
              <Num disabled={!editable} value={s.mitigation_cap} onChange={(v) => upd((x) => (x.scoring.mitigation_cap = v))} />
            </dd>
            <dt>Residual floor (residual &ge; ratio x inherent)</dt>
            <dd>
              <Num disabled={!editable} value={s.residual_floor_ratio} onChange={(v) => upd((x) => (x.scoring.residual_floor_ratio = v))} />
            </dd>
          </dl>
          <p className="label mt-4">Tier lower bounds (residual, 1-25)</p>
          <div className="flex gap-2">
            {(s.tiers as { name: string; min: number }[]).map((t, i) => (
              <div key={t.name}>
                <p className="text-xs text-slate-500">{t.name}</p>
                <Num step={0.5} disabled={!editable || i === 0} value={t.min} onChange={(v) => upd((x) => (x.scoring.tiers[i].min = v))} />
              </div>
            ))}
          </div>
        </Card>

        <Card title="Workflow and governance">
          <dl className="grid grid-cols-[1fr_auto] items-center gap-2 text-sm">
            <dt>Committee quorum</dt>
            <dd>
              <Num testId="quorum" step={1} disabled={!editable} value={w.quorum} onChange={(v) => upd((x) => (x.workflow.quorum = v))} />
            </dd>
            <dt>Outcome on a tied vote</dt>
            <dd>
              <select disabled={!editable} className="input w-32" value={w.tie_outcome} onChange={(e) => upd((x) => (x.workflow.tie_outcome = e.target.value))}>
                <option>DEFERRED</option>
                <option>REJECTED</option>
              </select>
            </dd>
            <dt>Second analyst when an override changes the tier</dt>
            <dd>
              <input type="checkbox" disabled={!editable} checked={w.second_analyst_on_tier_change} onChange={(e) => upd((x) => (x.workflow.second_analyst_on_tier_change = e.target.checked))} />
            </dd>
            <dt>Minimum override reason length</dt>
            <dd>
              <Num step={1} disabled={!editable} value={w.min_override_reason_chars} onChange={(v) => upd((x) => (x.workflow.min_override_reason_chars = v))} />
            </dd>
          </dl>
        </Card>

        <Card title="Version history">
          <ul className="space-y-1 text-sm" data-testid="config-history">
            {history.data?.map((h) => (
              <li key={h.id} className="border-t border-slate-100 pt-1">
                <span className="font-mono text-xs">v{h.version}</span> {h.note} <span className="text-xs text-slate-400">by {h.created_by}, {new Date(h.created_at).toLocaleString()}</span>
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <Card title={`Rating rules (${draft.rules.length}) - deterministic; AI only suggests where no rule fires`}>
        <div className="max-h-96 overflow-auto">
          <table className="w-full text-xs">
            <thead className="sticky top-0 bg-white text-left text-slate-500">
              <tr>
                <th>Id</th>
                <th>Dim</th>
                <th>When</th>
                <th>L</th>
                <th>I</th>
                <th>Risk types</th>
                <th>Policy</th>
              </tr>
            </thead>
            <tbody>
              {draft.rules.map((r: Cfg) => (
                <tr key={r.id} className="border-t border-slate-100">
                  <td className="py-1 font-mono">{r.id}</td>
                  <td>{r.dim}</td>
                  <td className="font-mono">{JSON.stringify(r.when)}</td>
                  <td>{r.likelihood}</td>
                  <td>{r.impact}</td>
                  <td>{r.risk_types.join(", ")}</td>
                  <td className="font-mono">{r.cite}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
      <ErrorText error={active.error} />
      {saving && (
        <ReasonDialog
          title="Save configuration as a new version"
          minChars={5}
          confirmLabel="Save version"
          hint="What changed and why, e.g. raised quorum to 4 after committee resizing"
          onClose={() => setSaving(false)}
          onSubmit={async (note) => {
            const r = await post<{ version: number }>("/config", { content: draft, note });
            setSaved(`Saved as version ${r.version}. New cases will use it; existing assessments keep their version.`);
            qc.invalidateQueries({ queryKey: ["config"] });
            qc.invalidateQueries({ queryKey: ["config-history"] });
          }}
        />
      )}
    </div>
  );
}
