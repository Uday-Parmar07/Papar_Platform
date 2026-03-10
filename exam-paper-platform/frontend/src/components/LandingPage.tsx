interface LandingPageProps {
  onStart: () => void
}

const features = [
  {
    title: 'Pattern Analysis',
    description: 'Learns historical trends from previous exam papers and recurring chapter distribution.',
  },
  {
    title: 'Topic-Based Prediction',
    description: 'Builds predictions around selected syllabus units and high-probability concepts.',
  },
  {
    title: 'Download-Ready Paper',
    description: 'Creates an exam-style question paper format that can be exported quickly.',
  },
]

export function LandingPage({ onStart }: LandingPageProps) {
  return (
    <section className="mx-auto grid w-full max-w-7xl gap-10 px-4 pb-8 pt-10 sm:px-6 lg:px-8 lg:pb-12 lg:pt-14">
      <div className="relative overflow-hidden rounded-3xl border border-brand-100 bg-gradient-to-br from-brand-50 via-white to-indigo-50 p-8 shadow-xl shadow-blue-100/70 sm:p-12">
        <div className="absolute -right-16 -top-16 h-44 w-44 rounded-full bg-brand-200/50 blur-2xl" />
        <div className="absolute -bottom-12 left-10 h-36 w-36 rounded-full bg-indigo-200/50 blur-2xl" />
        <div className="relative grid gap-6">
          <span className="w-fit rounded-full bg-brand-100 px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em] text-brand-700">
            AI-powered academic assistant
          </span>
          <h1 className="max-w-3xl text-3xl font-semibold tracking-tight text-slate-900 sm:text-5xl">
            Predict Your Next Exam Paper Using AI
          </h1>
          <p className="max-w-2xl text-sm leading-relaxed text-slate-600 sm:text-base">
            Analyze previous university papers, detect topic patterns, and generate a predicted exam paper tailored to
            your branch and chosen subjects.
          </p>
          <div>
            <button
              onClick={onStart}
              className="rounded-xl bg-brand-600 px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-blue-200 transition hover:bg-brand-700"
            >
              Generate Predicted Paper
            </button>
          </div>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        {features.map((feature) => (
          <article
            key={feature.title}
            className="animate-fade-in-up rounded-2xl border border-slate-200 bg-white p-6 shadow-sm shadow-slate-200/70"
          >
            <h2 className="text-lg font-semibold text-slate-900">{feature.title}</h2>
            <p className="mt-2 text-sm leading-relaxed text-slate-600">{feature.description}</p>
          </article>
        ))}
      </div>
    </section>
  )
}
