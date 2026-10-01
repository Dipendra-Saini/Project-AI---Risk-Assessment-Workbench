import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, post, type CaseDetail } from "../api";
import { useAuth } from "../auth";
import { ControlsEditor, FactorTable, NarrativePanel, OverridesPanel, ScoreSummary } from "../components/Assessment";
import { CommitteePanel, DecisionBanner, VotesList } from "../components/Committee";
import { AnalystActions, GateStrip } from "../components/Gates";
import { ExtractionTable, IntakePanel } from "../components/Intake";
import { Button, Card, ErrorText, Spinner, StatusPill, TierBadge, cx } from "../components/ui";
import { useCase, useCaseAction } from "../hooks";

const PIPELINE = [
  ["classify_change", "Classify"],
  ["extract_documents", "Extract"],
  ["po_gate", "PO confirms"],
  ["retrieve_policy", "Retrieve policy"],
  ["assess_factors", "Rate factors"],
  ["score", "Score"],
  ["draft_assessment", "Draft"],
  ["critique", "Critic"],
  ["handoff_to_analyst", "Hand-off"],
  ["analyst_gate", "Analyst review"],
] as const;

function PipelineBar({ c }: { c: CaseDetail }) {
  const current = c.pipeline_state === "running" ? c.pipeline_step : c.waiting_at;
  const idx = PIPELINE.findIndex(([k]) => k === current);
  return (
    <ol className="flex flex-wrap gap-1 text-[11px]" data-testid="pipeline-bar">
      {PIPELINE.map(([k, label], i) => (
        <li
          key={k}
          className={cx(
            "rounded px-2 py-0.5",
            i < idx && "bg-indigo-100 text-indigo-800",
            i === idx && (c.pipeline_state === "running" ? "animate-pulse bg-indigo-600 text-white" : "bg-amber-200 text-amber-900"),
            i > idx && "bg-slate-100 text-slate-500",
          )}
        >
          {label}
        </li>
      ))}
    </ol>
  );
}

function ExaminerPackButton({ id }: { id: number }) {
  const [err, setErr] = useState<unknown>(null);
  return (
    <>
      <Button
        variant="secondary"
        data-testid="examiner-pack"
        onClick={async () => {
          try {
            const html = await api<string>(`/cases/${id}/examiner-pack?format=html`);
            const url = URL.createObjectURL(new Blob([html], { type: "text/html" }));
            window.open(url, "_blank");
          } catch (e) {
            setErr(e);
          }
        }}
      >
        Examiner pack
      </Button>
      <ErrorText error={err} />
    </>
  );
}

interface AuditRow {
  seq: number;
  ts: string;
  actor: string;
  action: string;
  payload: Record<string, unknown>;
  hash: string;
}

function CaseActivity({ id }: { id: number }) {
  const q = useQuery({ queryKey: ["audit", id], queryFn: () => api<AuditRow[]>(`/audit?case_id=${id}`) });
  return (
    <Card title="Activity (hash-chained audit trail)" testId="case-activity">
      {q.isLoading && <Spinner />}
      <ol className="space-y-1 text-xs">
        {q.data?.map((e) => (
          <li key={e.seq} className="grid grid-cols-[3rem_9rem_6rem_1fr] gap-2 border-t border-slate-100 pt-1">
            <span className="font-mono text-slate-400">#{e.seq}</span>
            <span className="text-slate-500">{new Date(e.ts).toLocaleString()}</span>
            <span className="font-medium">{e.actor}</span>
            <span>
              <span className="font-mono text-indigo-700">{e.action}</span>{" "}
              <span className="text-slate-500">{JSON.stringify(e.payload).slice(0, 180)}</span>
            </span>
          </li>
        ))}
      </ol>
    </Card>
  );
}

function AiUsage({ c }: { c: CaseDetail }) {
  const u = c.ai_usage;
  return (
    <Card title="AI usage on this case" testId="ai-usage">
      <dl className="grid grid-cols-2 gap-2 text-sm">
        <dt className="text-slate-500">LLM calls</dt>
        <dd className="font-mono">{u.calls}</dd>
        <dt className="text-slate-500">Tokens in / out</dt>
        <dd className="font-mono">
          {u.input_tokens} / {u.output_tokens}
        </dd>
        <dt className="text-slate-500">Cache hits</dt>
        <dd className="font-mono">{u.cache_hits}</dd>
        <dt className="text-slate-500">Deterministic fallbacks</dt>
        <dd className="font-mono">{u.fallbacks}</dd>
      </dl>
    </Card>
  );
}

function ReadOnlyAssessment({ c }: { c: CaseDetail }) {
  return (
    <>
      <ScoreSummary c={c} />
      <FactorTable c={c} editable={false} />
      <ControlsEditor c={c} editable={false} />
      <NarrativePanel c={c} editable={false} />
      <OverridesPanel c={c} canAck={false} />
    </>
  );
}

export default function CaseView() {
  const id = Number(useParams().id);
  const { user } = useAuth();
  const q = useCase(id);
  const act = useCaseAction(id);
  const [tab, setTab] = useState<"case" | "facts" | "activity">("case");
  if (q.isLoading) return <Spinner label="loading case" />;
  if (q.error || !q.data) return <ErrorText error={q.error ?? "not found"} />;
  const c = q.data;
  const role = user!.role;
  const running = c.pipeline_state === "running";
  const analystEditable = role === "analyst" && c.status === "ANALYST_REVIEW" && !running;

  let body;
  if (role === "product_owner" && ["DRAFT", "INFO_REQUESTED"].includes(c.status)) {
    body = <IntakePanel c={c} />;
  } else if (running || !c.assessment) {
    body = (
      <Card title="Assessment in progress">
        {running ? <Spinner label={`Pipeline running: ${c.pipeline_step || "starting"}`} /> : <p className="text-sm text-slate-500">Waiting for the product owner to submit.</p>}
        {c.pipeline_state === "failed" && <p className="mt-2 text-sm text-rose-700">The pipeline failed. An analyst can re-run it.</p>}
      </Card>
    );
  } else if (role === "analyst" && c.status === "ANALYST_REVIEW") {
    body = (
      <>
        <ScoreSummary c={c} />
        <FactorTable c={c} editable={analystEditable} />
        <ControlsEditor c={c} editable={analystEditable} />
        <NarrativePanel c={c} editable={analystEditable} />
        <OverridesPanel c={c} canAck />
        <AnalystActions c={c} />
      </>
    );
  } else if (role === "committee" && c.status === "COMMITTEE_REVIEW") {
    body = (
      <>
        <CommitteePanel c={c} />
        <ReadOnlyAssessment c={c} />
      </>
    );
  } else if (role === "product_owner") {
    body = (
      <>
        <DecisionBanner c={c} />
        <Card title="Where your change request is">
          <p className="text-sm text-slate-600">
            {c.status === "ANALYST_REVIEW" && "An FCRM analyst is reviewing the assessment."}
            {c.status === "COMMITTEE_REVIEW" && "The risk committee is reviewing the assessment."}
            {c.status === "SUBMITTED" || c.status === "IN_ASSESSMENT" ? "The assessment is being prepared." : null}
            {c.decisions.length > 0 && "The committee has decided. See above."}
          </p>
          {c.assessment && (
            <p className="mt-2 text-sm">
              Residual risk: <TierBadge tier={c.assessment.residual_tier} score={c.assessment.residual} />
            </p>
          )}
        </Card>
      </>
    );
  } else {
    body = (
      <>
        <DecisionBanner c={c} />
        {c.status === "DEFERRED" && role === "analyst" && (
          <Card title="Deferred by the committee">
            <Button data-testid="reopen" onClick={() => act.mutate(() => post(`/cases/${c.id}/reopen`))}>
              Reopen for analyst review
            </Button>
            <ErrorText error={act.error} />
          </Card>
        )}
        {c.votes.length > 0 && (
          <Card title="Committee votes">
            <VotesList c={c} />
          </Card>
        )}
        <ReadOnlyAssessment c={c} />
      </>
    );
  }

  return (
    <div className="space-y-4" data-testid="case-view">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <Link to="/" className="text-xs text-indigo-700">
            &larr; all cases
          </Link>
          <h1 className="mt-1 text-xl font-semibold">
            <span className="font-mono text-sm text-slate-500" data-testid="case-ref">
              {c.ref}
            </span>{" "}
            {c.title}
          </h1>
          <div className="mt-1 flex items-center gap-2 text-sm text-slate-500">
            <StatusPill status={c.status} />
            <TierBadge tier={c.residual_tier} score={c.residual} />
            <span>
              {c.change_type.replaceAll("_", " ")} - {c.business_line} - by {c.created_by}
            </span>
          </div>
        </div>
        <ExaminerPackButton id={c.id} />
      </div>

      {c.warnings.length > 0 && (
        <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-900" data-testid="case-warnings">
          {c.warnings.map((w) => (
            <p key={w}>! {w}</p>
          ))}
        </div>
      )}
      <PipelineBar c={c} />
      {role !== "product_owner" && <GateStrip c={c} />}

      {role !== "product_owner" && (
        <nav className="flex gap-1 border-b border-slate-200 text-sm">
          {(["case", "facts", "activity"] as const).map((t) => (
            <button
              key={t}
              data-testid={`tab-${t}`}
              onClick={() => setTab(t)}
              className={cx("-mb-px border-b-2 px-3 py-2", tab === t ? "border-indigo-600 font-medium text-indigo-700" : "border-transparent text-slate-500")}
            >
              {{ case: "Assessment", facts: "Intake facts", activity: "Activity" }[t]}
            </button>
          ))}
        </nav>
      )}

      <div className="grid gap-4 lg:grid-cols-[1fr_18rem]">
        <div className="min-w-0 space-y-4">
          {tab === "case" && body}
          {tab === "facts" && (
            <Card title="Facts confirmed by the product owner">
              <ExtractionTable c={c} editable={false} />
            </Card>
          )}
          {tab === "activity" && <CaseActivity id={c.id} />}
          <ErrorText error={act.error} />
        </div>
        <aside className="space-y-4">
          <Card title="Description">
            <p className="text-sm whitespace-pre-wrap text-slate-600">{c.description}</p>
          </Card>
          {role !== "product_owner" && <AiUsage c={c} />}
        </aside>
      </div>
    </div>
  );
}
