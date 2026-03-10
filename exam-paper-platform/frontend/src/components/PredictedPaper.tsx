interface PredictedPaperData {
  subject: string
  duration: number
  totalMarks: number
  shortQuestions: string[]
  numericalQuestions: string[]
  longQuestions: string[]
}

interface PredictedPaperProps {
  paper: PredictedPaperData
  onRegenerate: () => void
  onModifyTopics: () => void
  onDownload: () => void
}

export function PredictedPaper({ onDownload, onModifyTopics, onRegenerate, paper }: PredictedPaperProps) {
  return (
    <section className="mx-auto grid w-full max-w-5xl gap-6 px-4 pb-10 pt-8 sm:px-6 lg:px-8">
      <article className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
        <header className="border-b border-dashed border-slate-300 pb-5 text-center">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-brand-700">Predicted Examination Paper</p>
          <h1 className="mt-2 text-2xl font-semibold text-slate-900">{paper.subject || 'Subject Name'}</h1>
          <p className="mt-1 text-sm text-slate-600">
            Time: {paper.duration} Hours | Max Marks: {paper.totalMarks}
          </p>
        </header>

        <div className="mt-6 space-y-6">
          <section>
            <h2 className="text-base font-semibold text-slate-900">Section A (Short Questions)</h2>
            <ol className="mt-2 list-decimal space-y-2 pl-5 text-sm text-slate-700">
              {paper.shortQuestions.map((question) => (
                <li key={question}>{question}</li>
              ))}
            </ol>
          </section>

          <section>
            <h2 className="text-base font-semibold text-slate-900">Section B (Numericals)</h2>
            <ol className="mt-2 list-decimal space-y-2 pl-5 text-sm text-slate-700">
              {paper.numericalQuestions.map((question) => (
                <li key={question}>{question}</li>
              ))}
            </ol>
          </section>

          <section>
            <h2 className="text-base font-semibold text-slate-900">Section C (Long Questions)</h2>
            <ol className="mt-2 list-decimal space-y-2 pl-5 text-sm text-slate-700">
              {paper.longQuestions.map((question) => (
                <li key={question}>{question}</li>
              ))}
            </ol>
          </section>
        </div>
      </article>

      <div className="flex flex-wrap items-center gap-3">
        <button
          onClick={onDownload}
          className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700"
        >
          Download PDF
        </button>
        <button
          onClick={onRegenerate}
          className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
        >
          Regenerate Paper
        </button>
        <button
          onClick={onModifyTopics}
          className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
        >
          Modify Topics
        </button>
      </div>
    </section>
  )
}
