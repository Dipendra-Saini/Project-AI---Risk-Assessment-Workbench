import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api, DIM_NAMES, post, type CaseDetail, type Factor } from "../api";
import { useAuth } from "../auth";
import { useCaseAction } from "../hooks";
import { CitationChip, ClaimText } from "./Citation";
import { Button, Card, ErrorText, OriginBadge, ReasonDialog, TierBadge, cx } from "./ui";

export function ScoreSummary({ c }: { c: CaseDetail }) {
  const a = c.assessment!;
  const [open, setOpen] = useState(false);
  return (
    <Card
      testId="score-summary"
      title="Risk score (deterministic engine, not AI)"
      actions={<span className="text-xs text-slate-400">config v{a.config_version_id} - hash {a.config_hash?.slice(0, 10)}</span>}
    >
      <div className="flex flex-wrap items-center gap-6">
        <div>
          <p className="label">Inherent</p>
          <TierBadge tier={a.inherent_tier} score={a.inherent} />
        </div>
        <div className="text-slate-300">-&gt; controls -&gt;</div>
        <div>
          <p className="label">Residual</p>
          <span data-testid="residual-tier">
            <TierBadge tier={a.residual_tier} score={a.residual} />
          </span>
        </div>
        <div>
          <p className="label">Risk types</p>
          <p className="text-sm">{a.risk_types.join(", ") || "-"}</p>
        </div>
        <Button variant="ghost" className="ml-auto" onClick={() => setOpen(!open)}>
          {open ? "Hide" : "Show"} calculation
        </Button>
      </div>
      {open && (
        <ol className="mt-3 list-decimal space-y-0.5 rounded bg-slate-50 p-3 pl-8 font-mono text-[11px] text-slate-700" data-testid="score-steps">
          {a.steps.map((s, i) => (
            <li key={i}>{s}</li>
          ))}
        </ol>
      )}
    </Card>
  );
}

function RatingSelect({ value, onChange, testId }: { value: number; onChange: (v: number) => void; testId: string }) {
  return (
    <select data-testid={testId} className="input" value={value} onChange={(e) => onChange(Number(e.target.value))}>
      {[1, 2, 3, 4, 5].map((n) => (
        <option key={n} value={n}>
          {n}
        </option>
      ))}
    </select>
  );
}

export function FactorTable({ c, editable }: { c: CaseDetail; editable: boolean }) {
  const act = useCaseAction(c.id);
  const [editing, setEditing] = useState<Factor | null>(null);
  const [lik, setLik] = useState(3);
  const [imp, setImp] = useState(3);
  const a = c.assessment!;
  return (
    <Card testId="factor-table" title="Risk factors by dimension (gate G1: confirm every AI suggestion)">
      <table className="w-full text-sm">
        <thead className="text-left text-xs text-slate-500">
          <tr>
            <th className="py-1">Dimension</th>
            <th>L</th>
            <th>I</th>
            <th>Inherent</th>
            <th>Mitigation</th>
            <th>Residual</th>
            <th>Source</th>
            <th>Basis</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {a.factors.map((f) => {
            const needsConfirm = ["ai", "offline", "pending"].includes(f.origin) && !f.confirmed;
            return (
              <tr key={f.dimension} data-testid={`factor-${f.dimension}`} className={cx("border-t border-slate-100 align-top", needsConfirm && "bg-fuchsia-50/40")}>
                <td className="py-2 pr-2">
                  <p className="font-medium">{DIM_NAMES[f.dimension] ?? f.dimension}</p>
                  <p className="text-[11px] text-slate-400">{f.risk_types.join(", ")}</p>
                </td>
                <td className="font-mono">{f.likelihood}</td>
                <td className="font-mono">{f.impact}</td>
                <td className="font-mono">{f.inherent?.toFixed(1)}</td>
                <td className="font-mono text-emerald-700">{f.mitigation ? `-${Math.round(f.mitigation * 100)}%` : "0%"}</td>
                <td className="font-mono font-semibold">
                  {f.residual?.toFixed(1)}
                  {f.floor_applied && <span title="residual floor applied" className="ml-1 text-[10px] text-slate-400">floor</span>}
                </td>
                <td>
                  <OriginBadge origin={f.origin} />
                  {f.confirmed && f.origin !== "rule" && <span className="ml-1 text-[11px] text-emerald-700">confirmed</span>}
                </td>
                <td className="max-w-xs pr-2 text-xs text-slate-600">
                  {f.rule_ids.length > 0 && <p className="font-mono text-[11px] text-slate-500">{f.rule_ids.join(", ")}</p>}
                  <p className="line-clamp-3">{f.rationale}</p>
                  {f.citations.map((id) => (
                    <CitationChip key={id} id={id} />
                  ))}
                </td>
                <td className="py-2 text-right whitespace-nowrap">
                  {editable && needsConfirm && f.origin !== "pending" && (
                    <Button
                      variant="secondary"
                      data-testid={`accept-${f.dimension}`}
                      onClick={() => act.mutate(() => post(`/cases/${c.id}/factors/${f.dimension}/accept`))}
                    >
                      Accept
                    </Button>
                  )}
                  {editable && (
                    <Button
                      variant="ghost"
                      data-testid={`override-${f.dimension}`}
                      onClick={() => {
                        setEditing(f);
                        setLik(f.likelihood);
                        setImp(f.impact);
                      }}
                    >
                      Override
                    </Button>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <ErrorText error={act.error} />
      {editing && (
        <ReasonDialog
          title={`Override ${DIM_NAMES[editing.dimension]}`}
          hint="e.g. Processor is unregulated in two corridors, so impact is higher than the rule assumes"
          onClose={() => setEditing(null)}
          onSubmit={(reason) =>
            act.mutateAsync(() => post(`/cases/${c.id}/factors/${editing.dimension}/override`, { likelihood: lik, impact: imp, reason }))
          }
        >
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">Likelihood (1-5)</label>
              <RatingSelect testId="override-likelihood" value={lik} onChange={setLik} />
            </div>
            <div>
              <label className="label">Impact (1-5)</label>
              <RatingSelect testId="override-impact" value={imp} onChange={setImp} />
            </div>
          </div>
          <p className="mt-2 text-xs text-slate-500">
            The score is recomputed straight away. If the residual tier changes, a second analyst must acknowledge before committee.
          </p>
        </ReasonDialog>
      )}
    </Card>
  );
}

interface LibControl {
  id: string;
  name: string;
  dims: string[];
  design: number;
  operating: number;
}

export function ControlsEditor({ c, editable }: { c: CaseDetail; editable: boolean }) {
  const act = useCaseAction(c.id);
  const a = c.assessment!;
  const lib = useQuery({ queryKey: ["controls"], queryFn: () => api<LibControl[]>("/controls"), enabled: editable });
  const [draft, setDraft] = useState<{ control_id: string; design: number; operating: number }[] | null>(null);
  const [adding, setAdding] = useState("");
  const [saving, setSaving] = useState(false);
  const rows = draft ?? a.controls.map((x) => ({ control_id: x.control_id, design: x.design, operating: x.operating }));
  const byId = Object.fromEntries(a.controls.map((x) => [x.control_id, x]));
  const libById = Object.fromEntries((lib.data ?? []).map((x) => [x.id, x]));
  const set = (i: number, k: "design" | "operating", v: number) => setDraft(rows.map((r, j) => (j === i ? { ...r, [k]: v } : r)));

  return (
    <Card
      testId="controls-editor"
      title="Mitigating controls"
      actions={
        editable && draft ? (
          <>
            <Button variant="secondary" onClick={() => setDraft(null)}>
              Discard
            </Button>
            <Button data-testid="save-controls" onClick={() => setSaving(true)}>
              Save and recompute
            </Button>
          </>
        ) : null
      }
    >
      {rows.length === 0 && <p className="text-sm text-slate-500">No controls mapped. Residual risk equals inherent risk.</p>}
      <table className="w-full text-sm">
        <tbody>
          {rows.map((r, i) => {
            const info = byId[r.control_id] ?? libById[r.control_id];
            return (
              <tr key={r.control_id} className="border-t border-slate-100" data-testid={`control-${r.control_id}`}>
                <td className="py-2 pr-2">
                  <p className="font-medium">
                    <span className="font-mono text-xs text-slate-500">{r.control_id}</span> {info?.name}
                  </p>
                  <p className="text-[11px] text-slate-400">
                    covers {info?.dims?.join(", ")}
                    {byId[r.control_id]?.matched_on && ` - matched on "${byId[r.control_id].matched_on}"`}
                  </p>
                </td>
                <td className="w-28 pr-2">
                  <label className="text-[10px] text-slate-400">design</label>
                  {editable ? (
                    <input type="number" min={0} max={1} step={0.05} className="input" value={r.design} onChange={(e) => set(i, "design", Number(e.target.value))} />
                  ) : (
                    <p className="font-mono">{r.design}</p>
                  )}
                </td>
                <td className="w-28 pr-2">
                  <label className="text-[10px] text-slate-400">operating</label>
                  {editable ? (
                    <input type="number" min={0} max={1} step={0.05} className="input" value={r.operating} onChange={(e) => set(i, "operating", Number(e.target.value))} />
                  ) : (
                    <p className="font-mono">{r.operating}</p>
                  )}
                </td>
                <td className="text-right">
                  {editable && (
                    <Button variant="ghost" onClick={() => setDraft(rows.filter((_, j) => j !== i))}>
                      Remove
                    </Button>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      {editable && lib.data && (
        <div className="mt-3 flex gap-2">
          <select data-testid="add-control" className="input" value={adding} onChange={(e) => setAdding(e.target.value)}>
            <option value="">Add a control from the library...</option>
            {lib.data
              .filter((l) => !rows.some((r) => r.control_id === l.id))
              .map((l) => (
                <option key={l.id} value={l.id}>
                  {l.id} - {l.name} ({l.dims.join(", ")})
                </option>
              ))}
          </select>
          <Button
            variant="secondary"
            disabled={!adding}
            onClick={() => {
              const l = libById[adding];
              setDraft([...rows, { control_id: l.id, design: l.design, operating: l.operating }]);
              setAdding("");
            }}
          >
            Add
          </Button>
        </div>
      )}
      {saving && (
        <ReasonDialog title="Save control changes" onClose={() => setSaving(false)} onSubmit={async (reason) => {
          await act.mutateAsync(() => api(`/cases/${c.id}/controls`, { method: "PUT", json: { controls: rows, reason } }));
          setDraft(null);
        }} />
      )}
    </Card>
  );
}

export function NarrativePanel({ c, editable }: { c: CaseDetail; editable: boolean }) {
  const act = useCaseAction(c.id);
  const a = c.assessment!;
  const [edit, setEdit] = useState<{ dim: string; text: string } | null>(null);
  const [signing, setSigning] = useState(false);
  const claims = a.critique?.claims ?? [];
  const n = a.narrative;
  const unsupported = a.critique?.unsupported ?? 0;
  if (!n) return <Card title="Assessment narrative">No narrative drafted yet.</Card>;
  const sections = [{ dimension: "SUMMARY", text: n.summary }, ...n.sections];

  return (
    <Card
      testId="narrative"
      title="Assessment narrative (AI draft, gate G2: analyst signs)"
      actions={
        <span className="text-xs text-slate-400">
          drafted by {a.narrative_provider} - checked by {a.critique?.checked_by ?? "-"}
        </span>
      }
    >
      {a.narrative_stale && (
        <div className="mb-3 flex items-center justify-between rounded border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900" data-testid="stale-banner">
          The factors changed after this narrative was drafted. Redraft or edit it before signing.
          {editable && (
            <Button data-testid="redraft" variant="secondary" onClick={() => act.mutate(() => post(`/cases/${c.id}/rerun`, { scope: "draft" }))}>
              Redraft with AI
            </Button>
          )}
        </div>
      )}
      <div className="mb-3 flex flex-wrap gap-3 text-xs" data-testid="critic-summary">
        <span className="rounded bg-emerald-50 px-2 py-1 text-emerald-800">{claims.filter((x) => x.status === "ok").length} claims verified</span>
        {unsupported > 0 && <span className="rounded bg-rose-50 px-2 py-1 text-rose-800">{unsupported} flagged by the critic: hover to see why</span>}
      </div>
      <div className="space-y-4">
        {sections.map((s) => (
          <div key={s.dimension} data-testid={`section-${s.dimension}`}>
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-semibold tracking-wide text-slate-500 uppercase">
                {s.dimension === "SUMMARY" ? "Summary" : DIM_NAMES[s.dimension] ?? s.dimension}
              </h3>
              {editable && (
                <Button variant="ghost" data-testid={`edit-section-${s.dimension}`} onClick={() => setEdit({ dim: s.dimension, text: s.text })}>
                  Edit
                </Button>
              )}
            </div>
            <p className="mt-1 text-sm leading-relaxed">
              <ClaimText text={s.text} claims={claims.filter((x) => x.dimension === s.dimension)} />
            </p>
          </div>
        ))}
        {n.suggested_conditions && n.suggested_conditions.length > 0 && (
          <div>
            <h3 className="text-xs font-semibold tracking-wide text-slate-500 uppercase">Conditions the committee may consider</h3>
            <ul className="mt-1 list-disc pl-5 text-sm">
              {n.suggested_conditions.map((x) => (
                <li key={x}>{x}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
      <p className="mt-4 rounded bg-slate-50 px-3 py-2 text-xs text-slate-500">
        The AI never recommends approve or reject. That decision belongs to the committee (ADR-006).
      </p>
      <div className="mt-4 flex items-center gap-3">
        {a.narrative_signed_by ? (
          <span className="text-sm text-emerald-700" data-testid="signed">
            Signed by {a.narrative_signed_by}
            {a.warnings_ack_reason && ` - critic warnings acknowledged: "${a.warnings_ack_reason}"`}
          </span>
        ) : (
          editable && (
            <Button
              data-testid="signoff"
              disabled={a.narrative_stale}
              onClick={() => (unsupported > 0 ? setSigning(true) : act.mutate(() => post(`/cases/${c.id}/narrative/signoff`, {})))}
            >
              Sign off narrative
            </Button>
          )
        )}
      </div>
      <ErrorText error={act.error} />
      {edit && (
        <ReasonDialog
          title={`Edit ${edit.dim === "SUMMARY" ? "summary" : DIM_NAMES[edit.dim]}`}
          minChars={10}
          onClose={() => setEdit(null)}
          onSubmit={(reason) => act.mutateAsync(() => post(`/cases/${c.id}/narrative/override`, { dimension: edit.dim, text: edit.text, reason }))}
        >
          <label className="label">Text (keep [chunk:ID] citations so every claim stays traceable)</label>
          <textarea data-testid="section-text" className="input min-h-40 font-mono text-xs" value={edit.text} onChange={(e) => setEdit({ ...edit, text: e.target.value })} />
        </ReasonDialog>
      )}
      {signing && (
        <ReasonDialog
          title="Sign off with unresolved critic warnings"
          confirmLabel="Sign off"
          hint="Explain why the flagged claims are acceptable, e.g. you checked the policy basis by hand"
          onClose={() => setSigning(false)}
          onSubmit={(reason) => act.mutateAsync(() => post(`/cases/${c.id}/narrative/signoff`, { warnings_reason: reason }))}
        >
          <p className="text-sm text-slate-600">{unsupported} claim(s) are still flagged by the critic. Your reason goes into the examiner pack.</p>
        </ReasonDialog>
      )}
    </Card>
  );
}

export function OverridesPanel({ c, canAck }: { c: CaseDetail; canAck: boolean }) {
  const act = useCaseAction(c.id);
  const { user } = useAuth();
  if (!c.overrides.length) return null;
  return (
    <Card testId="overrides" title={`Human overrides (${c.overrides.length})`}>
      <ul className="space-y-2">
        {c.overrides.map((o) => (
          <li key={o.id} className="rounded border border-slate-100 p-2 text-sm" data-testid={`override-row-${o.id}`}>
            <div className="flex items-center justify-between gap-2">
              <p>
                <span className="font-medium">
                  {o.target_type} {o.target_key}
                </span>{" "}
                by {o.by}
                {o.tier_before && o.tier_after && o.tier_before !== o.tier_after && (
                  <span className="ml-2 text-xs">
                    tier <TierBadge tier={o.tier_before} /> -&gt; <TierBadge tier={o.tier_after} />
                  </span>
                )}
              </p>
              {o.requires_ack &&
                (o.acked_by ? (
                  <span className="text-xs text-emerald-700">acknowledged by {o.acked_by}</span>
                ) : canAck && user?.id !== o.by_id ? (
                  <Button data-testid={`ack-${o.id}`} variant="secondary" onClick={() => act.mutate(() => post(`/cases/${c.id}/overrides/${o.id}/ack`))}>
                    Acknowledge as second analyst
                  </Button>
                ) : (
                  <span className="text-xs font-medium text-amber-700" data-testid="awaiting-ack">
                    awaiting second analyst
                  </span>
                ))}
            </div>
            <p className="mt-1 text-xs text-slate-500 italic">"{o.reason}"</p>
          </li>
        ))}
      </ul>
      <ErrorText error={act.error} />
    </Card>
  );
}
