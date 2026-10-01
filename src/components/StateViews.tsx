export function Loading() {
  return (
    <div role="status" className="py-10 text-center text-slate-500">
      Carregando…
    </div>
  );
}

export function Empty({ text }: { text: string }) {
  return <div className="card py-8 text-center text-slate-500">{text}</div>;
}

export function ErrorBox({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="card border-red-200 bg-red-50 text-red-800">
      <p>{message}</p>
      {onRetry && (
        <button className="btn-ghost mt-3" onClick={onRetry}>
          Tentar novamente
        </button>
      )}
    </div>
  );
}

export function Success({ text }: { text: string }) {
  return (
    <div role="status" className="rounded-xl bg-emerald-50 px-3 py-2 text-emerald-800">
      {text}
    </div>
  );
}
