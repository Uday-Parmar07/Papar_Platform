interface LoadingScreenProps {
  message: string
}

export function LoadingScreen({ message }: LoadingScreenProps) {
  return (
    <section className="mx-auto flex min-h-[65vh] w-full max-w-2xl flex-col items-center justify-center gap-6 px-4 text-center sm:px-6">
      <div className="relative">
        <div className="h-20 w-20 rounded-full border-4 border-brand-200" />
        <div className="absolute inset-0 h-20 w-20 animate-spin rounded-full border-4 border-transparent border-t-brand-600" />
      </div>
      <h2 className="text-2xl font-semibold tracking-tight text-slate-900">Generating Predicted Paper</h2>
      <p className="text-sm text-slate-600">{message}</p>
      <div className="flex items-center gap-1">
        <span className="h-2 w-2 animate-pulse rounded-full bg-brand-500 [animation-delay:0ms]" />
        <span className="h-2 w-2 animate-pulse rounded-full bg-brand-500 [animation-delay:150ms]" />
        <span className="h-2 w-2 animate-pulse rounded-full bg-brand-500 [animation-delay:300ms]" />
      </div>
    </section>
  )
}
