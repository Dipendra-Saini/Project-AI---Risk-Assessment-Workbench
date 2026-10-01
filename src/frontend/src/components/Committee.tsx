import { useState } from "react";
import { post, type CaseDetail } from "../api";
import { useAuth } from "../auth";
import { useCaseAction } from "../hooks";
import { Button, Card, ErrorText, ReasonDialog, cx } from "./ui";

const VOTES = [
  ["APPROVE", "Approve"],
  ["APPROVE_WITH_CONDITIONS", "Approve with conditions"],
  ["REJECT", "Reject"],
  ["DEFER", "Defer (need more information)"],
] as const;

export function VotesList({ c }: { c: CaseDetail }) {
  const round = c.votes.filter((v) => v.round === c.committee_round);
  return (
    <ul className="space-y-2" data-testid="votes">
      {round.map((v) => (
        <li key={v.member_id} className="rounded border border-slate-100 p-2 text-sm">
          <span className="font-medium">{v.member}</span>:{" "}
          {v.conflict ? <span className="text-slate-500">declared a conflict of interest (excluded from quorum)</span> : <span className="font-semibold">{v.vote?.replaceAll("_", " ").toLowerCase()}</span>}
          {v.rationale && <p className="mt-0.5 text-xs text-slate-500 italic">"{v.rationale}"</p>}
          {v.conditions.length > 0 && (
            <ul className="mt-1 list-disc pl-5 text-xs">
              {v.conditions.map((x) => (
                <li key={x}>{x}</li>
              ))}
            </ul>
          )}
        </li>
      ))}
      {round.length === 0 && <li className="text-sm text-slate-500">No votes yet in round {c.committee_round}.</li>}
    </ul>
  );
}

export function CommitteePanel({ c }: { c: CaseDetail }) {
  const act = useCaseAction(c.id);
  const { user } = useAuth();
  const [vote, setVote] = useState<string>("APPROVE_WITH_CONDITIONS");
  const [rationale, setRationale] = useState("");
  const [conditions, setConditions] = useState((c.assessment?.narrative?.suggested_conditions ?? []).join("\n"));
  const [conflict, setConflict] = useState(false);
  const [returning, setReturning] = useState(false);
  const voted = c.votes.some((v) => v.round === c.committee_round && v.member_id === user?.id);
  const eligible = c.votes.filter((v) => v.round === c.committee_round && !v.conflict).length;

  return (
    <Card testId="committee-panel" title={`Committee vote - round ${c.committee_round} (gate G3)`}>
      <VotesList c={c} />
      <p className="mt-2 text-xs text-slate-500" data-testid="quorum">
        {eligible} eligible vote(s) cast. Quorum and majority come from the active config. A tie gives the configured safe outcome, never an approval.
      </p>
      {!voted ? (
        <div className="mt-4 space-y-3 rounded-lg border border-slate-200 p-3">
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" data-testid="conflict" checked={conflict} onChange={(e) => setConflict(e.target.checked)} />I have a conflict of interest on this
            change (my vote won't count)
          </label>
          {!conflict && (
            <>
              <div className="grid grid-cols-2 gap-2">
                {VOTES.map(([v, label]) => (
                  <label key={v} className={cx("flex cursor-pointer items-center gap-2 rounded border px-3 py-2 text-sm", vote === v ? "border-indigo-500 bg-indigo-50" : "border-slate-200")}>
                    <input type="radio" name="vote" value={v} data-testid={`vote-${v}`} checked={vote === v} onChange={() => setVote(v)} />
                    {label}
                  </label>
                ))}
              </div>
              <div>
                <label className="label">Rationale</label>
                <textarea data-testid="vote-rationale" className="input min-h-20" value={rationale} onChange={(e) => setRationale(e.target.value)} />
              </div>
              {vote === "APPROVE_WITH_CONDITIONS" && (
                <div>
                  <label className="label">Conditions (one per line)</label>
                  <textarea data-testid="vote-conditions" className="input min-h-20" value={conditions} onChange={(e) => setConditions(e.target.value)} />
                </div>
              )}
            </>
          )}
          <Button
            data-testid="cast-vote"
            onClick={() =>
              act.mutate(() =>
                post(`/cases/${c.id}/votes`, { vote: conflict ? null : vote, rationale, conflict, conditions: conditions.split("\n").filter((x) => x.trim()) }),
              )
            }
          >
            {conflict ? "Declare conflict" : "Cast vote"}
          </Button>
        </div>
      ) : (
        <p className="mt-3 text-sm text-emerald-700">You have voted in this round.</p>
      )}
      <div className="mt-4 flex gap-2 border-t border-slate-100 pt-3">
        <Button data-testid="record-decision" onClick={() => act.mutate(() => post(`/cases/${c.id}/decision`))}>
          Record decision
        </Button>
        <Button variant="secondary" data-testid="return-to-analyst" onClick={() => setReturning(true)}>
          Return to analyst
        </Button>
      </div>
      <ErrorText error={act.error} />
      {returning && (
        <ReasonDialog
          title="Return to analyst"
          confirmLabel="Return"
          onClose={() => setReturning(false)}
          onSubmit={(note) => act.mutateAsync(() => post(`/cases/${c.id}/return-to-analyst`, { note }))}
        />
      )}
    </Card>
  );
}

export function DecisionBanner({ c }: { c: CaseDetail }) {
  const d = c.decisions[c.decisions.length - 1];
  if (!d) return null;
  const good = d.outcome.startsWith("APPROVED");
  return (
    <div className={cx("rounded-lg border p-4", good ? "border-emerald-200 bg-emerald-50" : "border-slate-200 bg-slate-100")} data-testid="decision">
      <p className="font-semibold">
        Committee decision: {d.outcome.replaceAll("_", " ").toLowerCase()} (round {d.round})
      </p>
      <p className="text-xs text-slate-600">
        recorded by {d.recorded_by} on {new Date(d.at).toLocaleString()}
      </p>
      {d.conditions.length > 0 && (
        <ul className="mt-2 list-disc pl-5 text-sm">
          {d.conditions.map((x) => (
            <li key={x}>{x}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
