export function Loading() {
  return (
    <div role="status" className="flex items-center justify-center gap-2 py-10 text-sm text-slate-500">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-slate-700" />
      Carregando…
    </div>
  );
}

export function Empty({ text }: { text: string }) {
  return (
    <div className="rounded-xl border border-dashed border-slate-300 bg-white px-4 py-10 text-center text-sm text-slate-500">
      {text}
    </div>
  );
}

export function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="callout callout-danger space-y-3 py-3">
      <p>{message}</p>
      {onRetry && (
        <button className="btn-ghost" onClick={onRetry}>
          Tentar novamente
        </button>
      )}
    </div>
  );
}

export function Success({ text }: { text: string }) {
  return (
    <div role="status" className="callout callout-ok">
      {text}
    </div>
  );
}