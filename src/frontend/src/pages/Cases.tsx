import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, post, type CaseDetail, type CaseSummary } from "../api";
import { useAuth } from "../auth";
import { Button, Card, Empty, ErrorText, Spinner, StatusPill, TierBadge } from "../components/ui";

const CHANGE_TYPES = ["new_product", "feature_change", "process_change", "vendor_onboarding", "new_geography", "new_customer_segment", "other"];

function NewCase({ onClose }: { onClose: () => void }) {
  const nav = useNavigate();
  const [f, setF] = useState({ title: "", description: "", change_type: "new_product", business_line: "", document_text: "" });
  const [err, setErr] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const set = (k: keyof typeof f) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value });
  return (
    <Card title="New change request" testId="new-case">
      <div className="grid gap-3 md:grid-cols-2">
        <div className="md:col-span-2">
          <label className="label">Title</label>
          <input data-testid="new-title" className="input" value={f.title} onChange={set("title")} placeholder="e.g. Cross-border instant payouts for gig workers" />
        </div>
        <div>
          <label className="label">Change type (AI will double-check)</label>
          <select className="input" value={f.change_type} onChange={set("change_type")}>
            {CHANGE_TYPES.map((t) => (
              <option key={t} value={t}>
                {t.replaceAll("_", " ")}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="label">Business line</label>
          <input data-testid="new-bl" className="input" value={f.business_line} onChange={set("business_line")} placeholder="Payments" />
        </div>
        <div className="md:col-span-2">
          <label className="label">Short description</label>
          <textarea data-testid="new-description" className="input min-h-16" value={f.description} onChange={set("description")} />
        </div>
        <div className="md:col-span-2">
          <label className="label">Product brief text (optional; you can upload PDF / DOCX next)</label>
          <textarea data-testid="new-document" className="input min-h-32 font-mono text-xs" value={f.document_text} onChange={set("document_text")} />
        </div>
      </div>
      <ErrorText error={err} />
      <div className="mt-3 flex justify-end gap-2">
        <Button variant="secondary" onClick={onClose}>
          Cancel
        </Button>
        <Button
          data-testid="create-case"
          disabled={busy || f.title.length < 5 || f.description.length < 10}
          onClick={async () => {
            setBusy(true);
            try {
              const c = await post<CaseDetail>("/cases", { ...f, document_text: f.document_text || null });
              nav(`/cases/${c.id}`);
            } catch (e) {
              setErr(e);
            } finally {
              setBusy(false);
            }
          }}
        >
          Create
        </Button>
      </div>
    </Card>
  );
}

const QUEUES: Record<string, { label: string; statuses: string | null }[]> = {
  product_owner: [{ label: "My change requests", statuses: null }],
  analyst: [
    { label: "Needs analyst review", statuses: "ANALYST_REVIEW" },
    { label: "In progress", statuses: "DRAFT,SUBMITTED,IN_ASSESSMENT,INFO_REQUESTED" },
    { label: "With committee", statuses: "COMMITTEE_REVIEW" },
    { label: "Decided", statuses: "APPROVED,APPROVED_WITH_CONDITIONS,REJECTED,DEFERRED" },
  ],
  committee: [
    { label: "Awaiting committee", statuses: "COMMITTEE_REVIEW" },
    { label: "Decided", statuses: "APPROVED,APPROVED_WITH_CONDITIONS,REJECTED,DEFERRED" },
    { label: "All", statuses: null },
  ],
};

export default function Cases() {
  const { user } = useAuth();
  const queues = QUEUES[user!.role];
  const [qi, setQi] = useState(0);
  const [creating, setCreating] = useState(false);
  const statuses = queues[qi].statuses;
  const q = useQuery({
    queryKey: ["cases", statuses],
    queryFn: () => api<CaseSummary[]>(`/cases${statuses ? `?status=${statuses}` : ""}`),
    refetchInterval: 5000,
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex gap-1">
          {queues.map((x, i) => (
            <button
              key={x.label}
              data-testid={`queue-${i}`}
              onClick={() => setQi(i)}
              className={`rounded-md px-3 py-1.5 text-sm ${i === qi ? "bg-indigo-600 text-white" : "text-slate-600 hover:bg-slate-100"}`}
            >
              {x.label}
            </button>
          ))}
        </div>
        {user!.role === "product_owner" && !creating && (
          <Button data-testid="new-case-button" onClick={() => setCreating(true)}>
            New change request
          </Button>
        )}
      </div>
      {creating && <NewCase onClose={() => setCreating(false)} />}
      <Card>
        {q.isLoading ? (
          <Spinner />
        ) : !q.data?.length ? (
          <Empty>No cases here.</Empty>
        ) : (
          <table className="w-full text-sm" data-testid="case-list">
            <thead className="text-left text-xs text-slate-500">
              <tr>
                <th className="py-1">Ref</th>
                <th>Title</th>
                <th>Status</th>
                <th>Residual</th>
                <th>Owner</th>
                <th>Updated</th>
              </tr>
            </thead>
            <tbody>
              {q.data.map((c) => (
                <tr key={c.id} className="border-t border-slate-100 hover:bg-slate-50" data-testid={`case-row-${c.ref}`}>
                  <td className="py-2 font-mono text-xs">
                    <Link to={`/cases/${c.id}`} className="text-indigo-700">
                      {c.ref}
                    </Link>
                  </td>
                  <td>
                    <Link to={`/cases/${c.id}`} className="font-medium hover:underline">
                      {c.title}
                    </Link>
                    {c.warnings.length > 0 && <span className="ml-2 rounded bg-rose-100 px-1.5 text-[11px] text-rose-800">warning</span>}
                    {c.pipeline_state === "running" && <span className="ml-2 text-[11px] text-indigo-600">running...</span>}
                  </td>
                  <td>
                    <StatusPill status={c.status} />
                  </td>
                  <td>
                    <TierBadge tier={c.residual_tier} score={c.residual} />
                  </td>
                  <td className="text-xs text-slate-500">{c.created_by}</td>
                  <td className="text-xs text-slate-500">{new Date(c.updated_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
