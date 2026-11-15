import { AlertTriangle } from 'lucide-react';

export function DegradedBanner({
  degraded,
  onRecover,
}: {
  degraded: boolean;
  onRecover?: () => void;
}) {
  if (!degraded) return null;
  return (
    <div
      role="alert"
      data-testid="degraded-banner"
      className="mb-4 flex items-center justify-between gap-3 rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900 shadow-sm"
    >
      <div className="flex items-center gap-2">
        <AlertTriangle className="h-4 w-4 shrink-0 text-amber-600" />
        <span>
          <strong>Marketplace Unavailable (Degraded Mode):</strong> Live marketplace tools are paused. Pending actions
          are safely queued for retry.
        </span>
      </div>
      {onRecover && (
        <button
          onClick={onRecover}
          className="rounded-lg border border-amber-400 bg-white px-3 py-1 text-xs font-medium text-amber-800 hover:bg-amber-100"
        >
          Retry Connection
        </button>
      )}
    </div>
  );
}
