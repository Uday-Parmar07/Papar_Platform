interface ExamSettingsProps {
  duration: number
  totalMarks: number
  difficulty: number
  totalQuestions: number
  useSectionDistribution: boolean
  sectionAShort: number
  sectionBMedium: number
  sectionCLong: number
  sectionSumMismatch: boolean
  autoBalanceTopics: boolean
  onDurationChange: (value: number) => void
  onMarksChange: (value: number) => void
  onDifficultyChange: (value: number) => void
  onTotalQuestionsChange: (value: number) => void
  onUseSectionDistributionChange: (value: boolean) => void
  onSectionAShortChange: (value: number) => void
  onSectionBMediumChange: (value: number) => void
  onSectionCLongChange: (value: number) => void
  onAutoBalanceTopicsChange: (value: boolean) => void
}

const difficultyText = ['Easy', 'Medium', 'Hard']

export function ExamSettings({
  autoBalanceTopics,
  difficulty,
  duration,
  onAutoBalanceTopicsChange,
  onDifficultyChange,
  onDurationChange,
  onMarksChange,
  onSectionAShortChange,
  onSectionBMediumChange,
  onSectionCLongChange,
  onTotalQuestionsChange,
  onUseSectionDistributionChange,
  sectionAShort,
  sectionBMedium,
  sectionCLong,
  sectionSumMismatch,
  totalMarks,
  totalQuestions,
  useSectionDistribution,
}: ExamSettingsProps) {
  const difficultyLabel = difficultyText[Math.round(difficulty)]

  return (
    <div className="grid gap-5">
      <section className="rounded-2xl border border-slate-200 bg-slate-50/70 p-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h3 className="text-sm font-semibold text-slate-900">Question Generation Settings</h3>
            <p className="mt-1 text-xs text-slate-600">Control how many questions are generated and how they are distributed.</p>
          </div>
        </div>

        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <label className="grid gap-1 text-sm">
            <span className="font-medium text-slate-700">Total Questions</span>
            <input
              type="number"
              min={4}
              max={40}
              value={totalQuestions}
              onChange={(event) => onTotalQuestionsChange(Number(event.target.value))}
              className="rounded-xl border border-slate-200 bg-white px-3 py-2 outline-none ring-brand-300 transition focus:border-brand-400 focus:ring"
            />
          </label>
          <label className="grid gap-2 text-sm">
            <span className="font-medium text-slate-700">Quick Adjust</span>
            <input
              type="range"
              min={4}
              max={40}
              step={1}
              value={totalQuestions}
              onChange={(event) => onTotalQuestionsChange(Number(event.target.value))}
              className="h-2 w-full cursor-pointer appearance-none rounded-full bg-slate-200 accent-brand-600"
            />
          </label>
        </div>

        <div className="mt-4 rounded-xl border border-slate-200 bg-white p-3">
          <label className="flex cursor-pointer items-center gap-2 text-sm font-medium text-slate-700">
            <input
              type="checkbox"
              checked={useSectionDistribution}
              onChange={(event) => onUseSectionDistributionChange(event.target.checked)}
              className="h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-400"
            />
            Section Distribution (optional)
          </label>

          {useSectionDistribution && (
            <div className="mt-3 grid gap-2 sm:grid-cols-3">
              <label className="grid gap-1 text-xs">
                <span className="font-medium text-slate-600">Section A - Short</span>
                <input
                  type="number"
                  min={0}
                  max={40}
                  value={sectionAShort}
                  onChange={(event) => onSectionAShortChange(Number(event.target.value))}
                  className="rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1.5 text-sm outline-none ring-brand-300 focus:border-brand-400 focus:ring"
                />
              </label>
              <label className="grid gap-1 text-xs">
                <span className="font-medium text-slate-600">Section B - Medium</span>
                <input
                  type="number"
                  min={0}
                  max={40}
                  value={sectionBMedium}
                  onChange={(event) => onSectionBMediumChange(Number(event.target.value))}
                  className="rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1.5 text-sm outline-none ring-brand-300 focus:border-brand-400 focus:ring"
                />
              </label>
              <label className="grid gap-1 text-xs">
                <span className="font-medium text-slate-600">Section C - Long</span>
                <input
                  type="number"
                  min={0}
                  max={40}
                  value={sectionCLong}
                  onChange={(event) => onSectionCLongChange(Number(event.target.value))}
                  className="rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-1.5 text-sm outline-none ring-brand-300 focus:border-brand-400 focus:ring"
                />
              </label>
            </div>
          )}

          {useSectionDistribution && sectionSumMismatch && (
            <p className="mt-2 rounded-lg border border-amber-200 bg-amber-50 px-2.5 py-1.5 text-xs text-amber-800">
              Section counts do not add up to total questions.
            </p>
          )}
        </div>

        <div className="mt-4 rounded-xl border border-blue-100 bg-blue-50/70 p-3">
          <label className="flex cursor-pointer items-center gap-2 text-sm font-medium text-blue-900">
            <input
              type="checkbox"
              checked={autoBalanceTopics}
              onChange={(event) => onAutoBalanceTopicsChange(event.target.checked)}
              className="h-4 w-4 rounded border-blue-300 text-brand-600 focus:ring-brand-400"
            />
            Auto-balance questions across topics
            <span
              title="When enabled, the system spreads questions across selected topics and supplements with related topics if data is limited."
              className="inline-flex h-5 w-5 items-center justify-center rounded-full border border-blue-200 bg-white text-xs text-blue-700"
            >
              i
            </span>
          </label>
        </div>
      </section>

      <div className="grid gap-3 sm:grid-cols-2">
        <label className="grid gap-1 text-sm">
          <span className="font-medium text-slate-700">Exam Duration (hours)</span>
          <input
            type="number"
            min={1}
            max={6}
            value={duration}
            onChange={(event) => onDurationChange(Number(event.target.value))}
            className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 outline-none ring-brand-300 transition focus:border-brand-400 focus:ring"
          />
        </label>
        <label className="grid gap-1 text-sm">
          <span className="font-medium text-slate-700">Total Marks</span>
          <input
            type="number"
            min={20}
            max={150}
            value={totalMarks}
            onChange={(event) => onMarksChange(Number(event.target.value))}
            className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 outline-none ring-brand-300 transition focus:border-brand-400 focus:ring"
          />
        </label>
      </div>

      <div className="grid gap-2">
        <div className="flex items-center justify-between text-sm">
          <span className="font-medium text-slate-700">Difficulty</span>
          <span className="rounded-full bg-indigo-100 px-2.5 py-0.5 text-xs font-semibold text-indigo-700">{difficultyLabel}</span>
        </div>
        <input
          type="range"
          title="Difficulty level"
          aria-label="Difficulty level"
          min={0}
          max={2}
          step={1}
          value={difficulty}
          onChange={(event) => onDifficultyChange(Number(event.target.value))}
          className="h-2 w-full cursor-pointer appearance-none rounded-full bg-slate-200 accent-brand-600"
        />
        <div className="flex justify-between text-xs text-slate-500">
          <span>Easy</span>
          <span>Medium</span>
          <span>Hard</span>
        </div>
      </div>

      <div className="rounded-2xl border border-indigo-100 bg-indigo-50/70 p-4">
        <h3 className="text-sm font-semibold text-indigo-900">Section Structure Preview</h3>
        <ul className="mt-2 space-y-1 text-sm text-indigo-800">
          <li>Section A: Short Questions</li>
          <li>Section B: Numericals</li>
          <li>Section C: Long Questions</li>
        </ul>
      </div>
    </div>
  )
}
