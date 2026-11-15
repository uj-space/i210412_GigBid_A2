import { useState } from 'react';
import { CheckCircle2, HelpCircle, XCircle } from 'lucide-react';

export interface ClaimVerificationItem {
  claim: string;
  verdict: 'supported' | 'partly_supported' | 'unsupported';
  evidence_id?: string | null;
  overlap?: number;
}

export function EvidenceHover({
  item,
  evidenceMap,
}: {
  item: ClaimVerificationItem;
  evidenceMap: Record<string, any>;
}) {
  const [open, setOpen] = useState(false);
  const ev = item.evidence_id ? evidenceMap[item.evidence_id] : null;

  const badgeClass =
    item.verdict === 'supported'
      ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
      : item.verdict === 'partly_supported'
      ? 'bg-amber-50 text-amber-700 border-amber-200'
      : 'bg-rose-50 text-rose-700 border-rose-200';

  const Icon =
    item.verdict === 'supported'
      ? CheckCircle2
      : item.verdict === 'partly_supported'
      ? HelpCircle
      : XCircle;

  return (
    <div
      className="relative rounded-lg border border-slate-200 bg-white p-3 text-sm"
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
    >
      <div className="flex items-start justify-between gap-2">
        <p className="text-slate-700">{item.claim}</p>
        <span className={`inline-flex shrink-0 items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium ${badgeClass}`}>
          <Icon className="h-3.5 w-3.5" />
          {item.evidence_id || item.verdict}
        </span>
      </div>
      {open && ev && (
        <div className="mt-2 rounded-lg border border-indigo-200 bg-indigo-50 p-2.5 text-xs text-slate-700">
          <div className="font-semibold text-indigo-900">
            {ev.title || ev.project} ({ev.evidence_id})
          </div>
          <div className="mt-0.5 text-slate-600">{ev.summary}</div>
          <div className="mt-1 flex flex-wrap gap-1.5 text-[11px] text-indigo-700">
            <span>Outcome: {ev.outcome || 'verified'}</span>
            {ev.client_industry && <span>· Industry: {ev.client_industry}</span>}
            {typeof item.overlap === 'number' && <span>· Overlap: {(item.overlap * 100).toFixed(0)}%</span>}
          </div>
        </div>
      )}
    </div>
  );
}
