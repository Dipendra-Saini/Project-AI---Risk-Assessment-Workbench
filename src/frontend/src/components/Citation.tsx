import { useState, type ReactNode } from "react";
import type { Claim } from "../api";
import { useChunk } from "../hooks";
import { Modal, Spinner, cx } from "./ui";

const CITE = /\[chunk:([A-Za-z0-9._-]+)\]/g;

export function CitationChip({ id }: { id: string }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button
        data-testid="citation-chip"
        onClick={() => setOpen(true)}
        className="mx-0.5 rounded bg-sky-50 px-1.5 py-0.5 align-baseline font-mono text-[11px] text-sky-800 ring-1 ring-sky-200 hover:bg-sky-100"
      >
        {id}
      </button>
      {open && <ChunkModal id={id} onClose={() => setOpen(false)} />}
    </>
  );
}

function ChunkModal({ id, onClose }: { id: string; onClose: () => void }) {
  const { data, isLoading, error } = useChunk(id);
  return (
    <Modal title={id} onClose={onClose}>
      {isLoading && <Spinner label="loading source" />}
      {error && <p className="text-sm text-rose-700">Source not found. A citation the system can't resolve is a defect.</p>}
      {data && (
        <div data-testid="chunk-text">
          <p className="text-xs text-slate-500">
            {data.doc_title} - {data.section_title}
          </p>
          <p className="mt-2 text-sm leading-relaxed whitespace-pre-wrap">{data.text}</p>
          {data.tags?.length > 0 && <p className="mt-3 text-xs text-slate-400">tags: {data.tags.join(", ")}</p>}
          {data.source_url && (
            <a className="mt-2 block text-xs text-indigo-700 underline" href={data.source_url} target="_blank" rel="noreferrer">
              public source
            </a>
          )}
        </div>
      )}
    </Modal>
  );
}

/** Render text with [chunk:ID] markers as clickable chips. */
export function WithCitations({ text }: { text: string }) {
  const out: ReactNode[] = [];
  let last = 0;
  for (const m of text.matchAll(CITE)) {
    out.push(text.slice(last, m.index));
    out.push(<CitationChip key={`${m.index}-${m[1]}`} id={m[1]} />);
    last = (m.index ?? 0) + m[0].length;
  }
  out.push(text.slice(last));
  return <>{out}</>;
}

const CLAIM_STYLE: Record<string, string> = {
  ok: "",
  doubtful: "bg-amber-50 decoration-amber-400 underline decoration-wavy underline-offset-4",
  unsupported: "bg-rose-50 decoration-rose-500 underline decoration-wavy underline-offset-4",
};

/** Section text split into the critic's claims, each highlighted by verdict. */
export function ClaimText({ text, claims }: { text: string; claims: Claim[] }) {
  if (!claims.length) return <WithCitations text={text} />;
  return (
    <>
      {claims.map((c) => (
        <span
          key={c.index}
          data-testid={`claim-${c.status}`}
          title={c.status === "ok" ? c.reason : `Critic: ${c.status} - ${c.reason}`}
          className={cx("rounded px-0.5", CLAIM_STYLE[c.status])}
        >
          <WithCitations text={c.text} />{" "}
        </span>
      ))}
    </>
  );
}
