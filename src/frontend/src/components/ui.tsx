import { useState, type ButtonHTMLAttributes, type ReactNode } from "react";

const cx = (...c: (string | false | null | undefined)[]) => c.filter(Boolean).join(" ");

export function Button({
  variant = "primary",
  className,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" | "danger" | "ghost" }) {
  const styles = {
    primary: "bg-indigo-600 text-white hover:bg-indigo-700 disabled:bg-indigo-300",
    secondary: "border border-slate-300 bg-white text-slate-700 hover:bg-slate-50 disabled:text-slate-400",
    danger: "bg-rose-600 text-white hover:bg-rose-700 disabled:bg-rose-300",
    ghost: "text-indigo-700 hover:bg-indigo-50 disabled:text-slate-400",
  }[variant];
  return (
    <button
      {...props}
      className={cx("rounded-md px-3 py-1.5 text-sm font-medium transition disabled:cursor-not-allowed", styles, className)}
    />
  );
}

export function Card({ title, actions, children, testId }: { title?: ReactNode; actions?: ReactNode; children: ReactNode; testId?: string }) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white shadow-sm" data-testid={testId}>
      {(title || actions) && (
        <header className="flex items-center justify-between gap-3 border-b border-slate-100 px-4 py-3">
          <h2 className="text-sm font-semibold text-slate-800">{title}</h2>
          <div className="flex items-center gap-2">{actions}</div>
        </header>
      )}
      <div className="p-4">{children}</div>
    </section>
  );
}

const TIER_STYLE: Record<string, string> = {
  Low: "bg-emerald-100 text-emerald-800 ring-emerald-200",
  Medium: "bg-amber-100 text-amber-800 ring-amber-200",
  High: "bg-orange-100 text-orange-800 ring-orange-300",
  Critical: "bg-rose-100 text-rose-800 ring-rose-300",
};

export function TierBadge({ tier, score }: { tier?: string | null; score?: number | null }) {
  if (!tier) return <span className="text-xs text-slate-400">-</span>;
  return (
    <span data-testid="tier-badge" className={cx("inline-flex items-center gap-1 whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-semibold ring-1", TIER_STYLE[tier])}>
      {tier}
      {score != null && <span className="font-normal opacity-75">{score.toFixed(1)}</span>}
    </span>
  );
}

const STATUS_STYLE: Record<string, string> = {
  DRAFT: "bg-slate-100 text-slate-700",
  SUBMITTED: "bg-sky-100 text-sky-800",
  IN_ASSESSMENT: "bg-sky-100 text-sky-800",
  ANALYST_REVIEW: "bg-violet-100 text-violet-800",
  INFO_REQUESTED: "bg-amber-100 text-amber-800",
  COMMITTEE_REVIEW: "bg-indigo-100 text-indigo-800",
  APPROVED: "bg-emerald-100 text-emerald-800",
  APPROVED_WITH_CONDITIONS: "bg-emerald-100 text-emerald-800",
  REJECTED: "bg-rose-100 text-rose-800",
  DEFERRED: "bg-slate-200 text-slate-700",
};

export function StatusPill({ status }: { status: string }) {
  return (
    <span data-testid="status-pill" className={cx("rounded px-2 py-0.5 text-xs font-medium whitespace-nowrap", STATUS_STYLE[status] ?? "bg-slate-100")}>
      {status.replaceAll("_", " ").toLowerCase()}
    </span>
  );
}

const ORIGIN: Record<string, [string, string]> = {
  rule: ["Rule", "bg-slate-100 text-slate-700"],
  ai: ["AI suggestion", "bg-fuchsia-100 text-fuchsia-800"],
  offline: ["AI fallback", "bg-fuchsia-50 text-fuchsia-700"],
  pending: ["Needs rating", "bg-amber-100 text-amber-800"],
  human: ["Analyst", "bg-indigo-100 text-indigo-800"],
  llm: ["AI", "bg-fuchsia-100 text-fuchsia-800"],
  mapped: ["Mapped", "bg-slate-100 text-slate-700"],
  po: ["Product owner", "bg-indigo-100 text-indigo-800"],
};

export function OriginBadge({ origin }: { origin: string }) {
  const [label, style] = ORIGIN[origin] ?? [origin, "bg-slate-100 text-slate-700"];
  return <span className={cx("rounded px-1.5 py-0.5 text-[11px] font-medium whitespace-nowrap", style)}>{label}</span>;
}

export function ErrorText({ error }: { error: unknown }) {
  if (!error) return null;
  return (
    <p role="alert" data-testid="error" className="mt-2 rounded border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-800">
      {error instanceof Error ? error.message : String(error)}
    </p>
  );
}

export function Modal({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-slate-900/40 p-4" onClick={onClose}>
      <div className="w-full max-w-lg rounded-lg bg-white shadow-xl" role="dialog" aria-label={title} onClick={(e) => e.stopPropagation()}>
        <header className="flex items-center justify-between border-b px-4 py-3">
          <h3 className="font-semibold">{title}</h3>
          <button className="text-slate-400 hover:text-slate-700" onClick={onClose} aria-label="close">
            x
          </button>
        </header>
        <div className="p-4">{children}</div>
      </div>
    </div>
  );
}

/** Every human change needs a reason (FR-12). The minimum length mirrors the server-side config check. */
export function ReasonDialog({
  title,
  hint,
  minChars = 15,
  confirmLabel = "Save",
  children,
  onSubmit,
  onClose,
}: {
  title: string;
  hint?: string;
  minChars?: number;
  confirmLabel?: string;
  children?: ReactNode;
  onSubmit: (reason: string) => Promise<unknown>;
  onClose: () => void;
}) {
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const ok = reason.trim().length >= minChars;
  return (
    <Modal title={title} onClose={onClose}>
      {children}
      <label className="label mt-2">Reason (recorded in the audit trail)</label>
      <textarea
        data-testid="reason-input"
        className="input min-h-24"
        value={reason}
        onChange={(e) => setReason(e.target.value)}
        placeholder={hint ?? "Why are you making this change?"}
        autoFocus
      />
      <p className="mt-1 text-xs text-slate-500">
        {reason.trim().length}/{minChars} characters minimum
      </p>
      <ErrorText error={error} />
      <div className="mt-4 flex justify-end gap-2">
        <Button variant="secondary" onClick={onClose}>
          Cancel
        </Button>
        <Button
          data-testid="reason-submit"
          disabled={!ok || busy}
          onClick={async () => {
            setBusy(true);
            setError(null);
            try {
              await onSubmit(reason.trim());
              onClose();
            } catch (e) {
              setError(e);
            } finally {
              setBusy(false);
            }
          }}
        >
          {busy ? "Saving..." : confirmLabel}
        </Button>
      </div>
    </Modal>
  );
}

export function Spinner({ label }: { label?: string }) {
  return (
    <span className="inline-flex items-center gap-2 text-sm text-slate-500" data-testid="spinner">
      <span className="h-3 w-3 animate-spin rounded-full border-2 border-indigo-500 border-t-transparent" />
      {label}
    </span>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <p className="py-6 text-center text-sm text-slate-500">{children}</p>;
}

export { cx };
