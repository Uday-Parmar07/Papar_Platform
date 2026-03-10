import type { Question } from '../types'

interface PreviewData {
  branch: string
  subject: string
  topics: string[]
  fromYear: number
  toYear: number
  duration: number
  totalMarks: number
  difficulty: string
}

interface PaperPreviewProps {
  data: PreviewData
  generatedQuestions?: Question[]
}

export function PaperPreview({ data, generatedQuestions = [] }: PaperPreviewProps) {
  const hasGenerated = generatedQuestions.length > 0

  const questions = hasGenerated
    ? {
        short: generatedQuestions
          .filter((question) => question.difficulty.toLowerCase().includes('easy'))
          .map((question) => question.question),
        numerical: generatedQuestions
          .filter((question) => {
            const level = question.difficulty.toLowerCase()
            return !level.includes('easy') && !level.includes('hard')
          })
          .map((question) => question.question),
        long: generatedQuestions
          .filter((question) => question.difficulty.toLowerCase().includes('hard'))
          .map((question) => question.question),
      }
    : {
        short: data.topics.slice(0, 4).map((topic, index) => `Q${index + 1}. Explain the concept of ${topic}.`),
        numerical: data.topics.slice(0, 3).map((topic, index) => `Q${index + 5}. Solve a numerical based on ${topic}.`),
        long: data.topics.slice(0, 3).map((topic, index) => `Q${index + 8}. Discuss applications and design aspects of ${topic}.`),
      }

  const shortQuestions = questions.short.length > 0 ? questions.short : questions.numerical.slice(0, 4)
  const numericalQuestions = questions.numerical.length > 0 ? questions.numerical : questions.short.slice(0, 3)
  const longQuestions = questions.long.length > 0 ? questions.long : questions.numerical.slice(0, 3)

  return (
    <aside className="h-full rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-brand-700">Live Preview</p>
      <h3 className="mt-1 text-lg font-semibold text-slate-900">Predicted Examination Paper</h3>
      {hasGenerated && (
        <p className="mt-1 text-[11px] font-medium uppercase tracking-wide text-emerald-700">Using generated backend output</p>
      )}
      <div className="mt-3 grid gap-2 text-xs text-slate-600">
        <p>
          <span className="font-semibold text-slate-800">Branch:</span> {data.branch || 'Select branch'}
        </p>
        <p>
          <span className="font-semibold text-slate-800">Subject:</span> {data.subject || 'Select subject'}
        </p>
        <p>
          <span className="font-semibold text-slate-800">Years:</span> {data.fromYear} - {data.toYear}
        </p>
        <p>
          <span className="font-semibold text-slate-800">Time:</span> {data.duration} Hours |{' '}
          <span className="font-semibold text-slate-800">Max Marks:</span> {data.totalMarks}
        </p>
        <p>
          <span className="font-semibold text-slate-800">Difficulty:</span> {data.difficulty}
        </p>
      </div>

      <div className="mt-4 space-y-4 text-xs">
        <section>
          <h4 className="font-semibold text-slate-800">Section A (Short Questions)</h4>
          <ul className="mt-1 space-y-1 text-slate-600">
            {shortQuestions.slice(0, 4).map((question) => (
              <li key={question}>{question}</li>
            ))}
          </ul>
        </section>
        <section>
          <h4 className="font-semibold text-slate-800">Section B (Numericals)</h4>
          <ul className="mt-1 space-y-1 text-slate-600">
            {numericalQuestions.slice(0, 3).map((question) => (
              <li key={question}>{question}</li>
            ))}
          </ul>
        </section>
        <section>
          <h4 className="font-semibold text-slate-800">Section C (Long Questions)</h4>
          <ul className="mt-1 space-y-1 text-slate-600">
            {longQuestions.slice(0, 3).map((question) => (
              <li key={question}>{question}</li>
            ))}
          </ul>
        </section>
      </div>
    </aside>
  )
}
