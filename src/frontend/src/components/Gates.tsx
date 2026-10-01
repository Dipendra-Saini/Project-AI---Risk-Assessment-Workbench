import { useState } from "react";
import { post, type CaseDetail } from "../api";
import { useCaseAction } from "../hooks";
import { Button, Card, ErrorText, ReasonDialog, cx } from "./ui";

const ORDER = ["G0", "G1", "G1b", "G2", "G3"] as const;

export function GateStrip({ c }: { c: CaseDetail }) {
  return (
    <ol className="grid grid-cols-5 gap-2" data-testid="gates">
      {ORDER.map((g) => {
        const s = c.gates[g];
        return (
          <li
            key={g}
            data-testid={`gate-${g}`}
            data-passed={s.passed}
            title={s.blocking.join("\n")}
            className={cx("rounded-md border px-3 py-2 text-xs", s.passed ? "border-emerald-200 bg-emerald-50 text-emerald-900" : "border-slate-200 bg-white text-slate-600")}
          >
            <p className="font-semibold">
              {s.passed ? "OK" : "o"} {g}
            </p>
            <p className="leading-tight">{s.label}</p>
          </li>
        );
      })}
    </ol>
  );
}

export function AnalystActions({ c }: { c: CaseDetail }) {
  const act = useCaseAction(c.id);
  const [asking, setAsking] = useState(false);
  const blockers = ORDER.slice(0, 4).flatMap((g) => c.gates[g].blocking);
  return (
    <Card testId="analyst-actions" title="Send to committee">
      {blockers.length > 0 ? (
        <ul className="mb-3 space-y-1 text-sm" data-testid="blockers">
          {blockers.map((b) => (
            <li key={b} className="text-amber-800">
              - {b}
            </li>
          ))}
        </ul>
      ) : (
        <p className="mb-3 text-sm text-emerald-700">All analyst gates passed.</p>
      )}
      <div className="flex flex-wrap gap-2">
        <Button data-testid="submit-committee" disabled={blockers.length > 0} onClick={() => act.mutate(() => post(`/cases/${c.id}/submit-to-committee`))}>
          Submit to committee
        </Button>
        <Button variant="secondary" data-testid="request-info" onClick={() => setAsking(true)}>
          Request info from product owner
        </Button>
        <Button variant="secondary" data-testid="rerun-full" onClick={() => act.mutate(() => post(`/cases/${c.id}/rerun`, { scope: "full" }))}>
          Re-run full assessment
        </Button>
      </div>
      <ErrorText error={act.error} />
      {asking && (
        <ReasonDialog
          title="Request information"
          minChars={10}
          confirmLabel="Send request"
          hint="e.g. Which corridors does PayRoute cover, and who screens payouts?"
          onClose={() => setAsking(false)}
          onSubmit={(message) => act.mutateAsync(() => post(`/cases/${c.id}/request-info`, { message }))}
        />
      )}
    </Card>
  );
}
