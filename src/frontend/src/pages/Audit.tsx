import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../api";
import { Button, Card, Spinner } from "../components/ui";

interface Row {
  seq: number;
  ts: string;
  actor: string;
  action: string;
  entity_type: string;
  entity_id: string;
  payload: Record<string, unknown>;
  hash: string;
  prev_hash: string;
}

export default function Audit() {
  const [filter, setFilter] = useState("");
  const rows = useQuery({ queryKey: ["audit-all"], queryFn: () => api<Row[]>("/audit?limit=500") });
  const verify = useQuery({ queryKey: ["audit-verify"], queryFn: () => api<{ valid: boolean; events: number; head_hash?: string; first_broken_seq?: number }>("/audit/verify"), enabled: false });
  const shown = (rows.data ?? []).filter((r) => !filter || `${r.actor} ${r.action} ${r.entity_id}`.toLowerCase().includes(filter.toLowerCase()));

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Audit trail</h1>
          <p className="text-sm text-slate-500">Append-only and hash-chained: each event stores the hash of the one before it, and the database refuses UPDATE and DELETE.</p>
        </div>
        <Button data-testid="verify-chain" onClick={() => verify.refetch()}>
          Verify chain integrity
        </Button>
      </div>
      {verify.data && (
        <p data-testid="verify-result" className={`rounded px-3 py-2 text-sm ${verify.data.valid ? "bg-emerald-50 text-emerald-800" : "bg-rose-50 text-rose-800"}`}>
          {verify.data.valid
            ? `Chain valid: ${verify.data.events} events, head ${verify.data.head_hash?.slice(0, 16)}`
            : `Chain BROKEN at event ${verify.data.first_broken_seq}: a stored event no longer matches its hash`}
        </p>
      )}
      <Card title={<input className="input w-72" placeholder="Filter by actor, action, case id" value={filter} onChange={(e) => setFilter(e.target.value)} />}>
        {rows.isLoading && <Spinner />}
        <table className="w-full text-xs" data-testid="audit-table">
          <thead className="text-left text-slate-500">
            <tr>
              <th>#</th>
              <th>Time</th>
              <th>Actor</th>
              <th>Action</th>
              <th>Entity</th>
              <th>Payload</th>
              <th>Hash</th>
            </tr>
          </thead>
          <tbody>
            {shown.map((r) => (
              <tr key={r.seq} className="border-t border-slate-100 align-top">
                <td className="py-1 font-mono text-slate-400">{r.seq}</td>
                <td className="whitespace-nowrap text-slate-500">{new Date(r.ts).toLocaleString()}</td>
                <td className="font-medium">{r.actor}</td>
                <td className="font-mono text-indigo-700">{r.action}</td>
                <td className="whitespace-nowrap">
                  {r.entity_type}:{r.entity_id}
                </td>
                <td className="max-w-md truncate text-slate-500" title={JSON.stringify(r.payload, null, 1)}>
                  {JSON.stringify(r.payload)}
                </td>
                <td className="font-mono text-slate-400" title={`prev ${r.prev_hash}`}>
                  {r.hash.slice(0, 10)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
