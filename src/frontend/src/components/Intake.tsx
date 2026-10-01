import { useRef, useState } from "react";
import { api, post, type CaseDetail, type Field } from "../api";
import { useCaseAction } from "../hooks";
import { Button, Card, ErrorText, OriginBadge, ReasonDialog, Spinner, cx } from "./ui";

const FIELD_LABEL: Record<string, string> = {
  customer_types: "Customer types",
  geographies: "Geographies",
  channels: "Delivery channels",
  third_parties: "Third parties",
  third_party_roles: "Third-party roles",
  cross_border: "Cross-border",
  cash: "Cash involved",
  crypto: "Crypto assets",
  instant_payments: "Instant payments",
  anonymous_or_prepaid: "Anonymous / prepaid",
  monthly_value_usd: "Monthly value (USD)",
  monthly_volume: "Monthly volume (txns)",
  proposed_controls: "Proposed controls",
};

export function formatValue(v: unknown): string {
  if (v === null || v === undefined || v === "") return "-";
  if (Array.isArray(v)) return v.length ? v.join(", ") : "none";
  if (typeof v === "boolean") return v ? "yes" : "no";
  if (typeof v === "number") return v.toLocaleString();
  return String(v);
}

function parseInput(raw: string, like: unknown): unknown {
  if (Array.isArray(like)) return raw.split(/[,;]\s*/).map((s) => s.trim()).filter(Boolean);
  if (typeof like === "boolean") return raw === "true";
  if (typeof like === "number" || like === null) return raw.trim() === "" ? null : Number(raw.replaceAll(",", ""));
  return raw;
}

export function ExtractionTable({ c, editable }: { c: CaseDetail; editable: boolean }) {
  const act = useCaseAction(c.id);
  const [editing, setEditing] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const ext = c.extraction;
  if (!ext) return null;
  const entries = Object.entries(ext.data) as [string, Field][];
  const current = editing ? ext.data[editing] : null;
  return (
    <>
      {ext.flags.length > 0 && (
        <ul className="mb-3 space-y-1" data-testid="extraction-flags">
          {ext.flags.map((f) => (
            <li key={f} className={cx("rounded px-3 py-1.5 text-xs", f.includes("injection") ? "bg-rose-50 text-rose-800" : "bg-amber-50 text-amber-800")}>
              {f}
            </li>
          ))}
        </ul>
      )}
      <table className="w-full text-sm" data-testid="extraction-table">
        <thead className="text-left text-xs text-slate-500">
          <tr>
            <th className="py-1 pr-2">Fact</th>
            <th className="py-1 pr-2">Value</th>
            <th className="py-1 pr-2">Evidence from the documents</th>
            <th className="py-1 pr-2">Confidence</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {entries.map(([k, f]) => (
            <tr key={k} className="border-t border-slate-100 align-top" data-testid={`fact-${k}`}>
              <td className="py-2 pr-2 font-medium whitespace-nowrap">{FIELD_LABEL[k] ?? k}</td>
              <td className="py-2 pr-2">
                <span data-testid={`fact-value-${k}`}>{formatValue(f.value)}</span> <OriginBadge origin={f.origin} />
              </td>
              <td className="max-w-md py-2 pr-2 text-xs text-slate-500 italic">{f.source_span ? `"${f.source_span}"` : "-"}</td>
              <td className="py-2 pr-2">
                <span className={cx("text-xs", f.confidence < 0.5 ? "font-semibold text-amber-700" : "text-slate-500")}>
                  {Math.round(f.confidence * 100)}%
                </span>
              </td>
              <td className="py-2 text-right">
                {editable && (
                  <Button
                    variant="ghost"
                    data-testid={`edit-${k}`}
                    onClick={() => {
                      setEditing(k);
                      setDraft(Array.isArray(f.value) ? f.value.join(", ") : f.value == null ? "" : String(f.value));
                    }}
                  >
                    Correct
                  </Button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-2 text-xs text-slate-400">
        Extracted by {ext.provider} with prompt {ext.prompt_version}, version {ext.version}
        {ext.confirmed && ` - confirmed by ${ext.confirmed_by}`}
      </p>
      {editing && current && (
        <ReasonDialog
          title={`Correct "${FIELD_LABEL[editing] ?? editing}"`}
          minChars={5}
          onClose={() => setEditing(null)}
          onSubmit={(reason) =>
            act.mutateAsync(() =>
              api<CaseDetail>(`/cases/${c.id}/extraction`, {
                method: "PATCH",
                json: { field: editing, value: parseInput(draft, current.value), reason },
              }),
            )
          }
        >
          <label className="label">New value</label>
          {typeof current.value === "boolean" ? (
            <select data-testid="value-input" className="input" value={draft} onChange={(e) => setDraft(e.target.value)}>
              <option value="true">yes</option>
              <option value="false">no</option>
            </select>
          ) : (
            <input data-testid="value-input" className="input" value={draft} onChange={(e) => setDraft(e.target.value)} />
          )}
          {Array.isArray(current.value) && <p className="mt-1 text-xs text-slate-500">Comma-separated list</p>}
        </ReasonDialog>
      )}
    </>
  );
}

export function IntakePanel({ c }: { c: CaseDetail }) {
  const act = useCaseAction(c.id);
  const fileRef = useRef<HTMLInputElement>(null);
  const running = c.pipeline_state === "running";
  const atGate = c.waiting_at === "po_gate";

  const upload = async (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    await act.mutateAsync(() => api<CaseDetail>(`/cases/${c.id}/documents`, { method: "POST", body: fd }));
  };

  return (
    <div className="space-y-4">
      {c.status === "INFO_REQUESTED" && c.info_request && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm" data-testid="info-request">
          <p className="font-semibold text-amber-900">The FCRM analyst asked for more information</p>
          <p className="mt-1 text-amber-900">{c.info_request}</p>
          <p className="mt-2 text-xs text-amber-800">Add a document or correct the facts below, re-run extraction, then resubmit.</p>
        </div>
      )}
      <Card
        title="1. Documents"
        actions={
          <>
            <input
              ref={fileRef}
              type="file"
              accept=".pdf,.docx,.txt,.md"
              className="hidden"
              data-testid="file-input"
              onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])}
            />
            <Button variant="secondary" onClick={() => fileRef.current?.click()}>
              Upload PDF / DOCX / TXT
            </Button>
          </>
        }
      >
        {c.documents.length === 0 ? (
          <p className="text-sm text-slate-500">No documents yet. Upload a product brief so the AI can extract the risk facts.</p>
        ) : (
          <ul className="space-y-2">
            {c.documents.map((d) => (
              <li key={d.id} className="rounded border border-slate-100 p-2 text-sm">
                <span className="font-medium">{d.filename}</span>{" "}
                <span className="text-xs text-slate-400">
                  {(d.size / 1024).toFixed(1)} KB - sha256 {d.sha256.slice(0, 10)}
                </span>
                <p className="mt-1 line-clamp-2 text-xs text-slate-500">{d.preview}</p>
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Card
        title="2. Check what the AI extracted (gate G0)"
        actions={
          <Button
            data-testid="run-extraction"
            variant={c.extraction ? "secondary" : "primary"}
            disabled={running || c.documents.length === 0}
            onClick={() => act.mutate(() => post(`/cases/${c.id}/extract`))}
          >
            {c.extraction ? "Re-run extraction" : "Run AI extraction"}
          </Button>
        }
      >
        {running ? (
          <Spinner label={`AI is reading the documents (${c.pipeline_step || "starting"})...`} />
        ) : c.extraction ? (
          <ExtractionTable c={c} editable />
        ) : (
          <p className="text-sm text-slate-500">Run extraction to see the facts the assessment will be based on.</p>
        )}
      </Card>

      <Card title="3. Confirm and submit">
        <p className="text-sm text-slate-600">
          By submitting you confirm these facts describe the change. The risk assessment runs on these facts, and an FCRM analyst reviews
          every AI suggestion before anything reaches the committee.
        </p>
        <Button
          className="mt-3"
          data-testid="submit-intake"
          disabled={!atGate || running}
          onClick={() => act.mutate(() => post(`/cases/${c.id}/submit`))}
        >
          Confirm facts and submit for assessment
        </Button>
        {!atGate && !running && c.extraction && <p className="mt-2 text-xs text-slate-500">Re-run extraction after adding documents.</p>}
        <ErrorText error={act.error} />
      </Card>
    </div>
  );
}
