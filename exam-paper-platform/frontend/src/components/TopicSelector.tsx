export interface TopicItem {
  name: string
  frequent?: boolean
  highWeightage?: boolean
}

interface TopicSelectorProps {
  topics: TopicItem[]
  selectedTopics: string[]
  customTopics: string[]
  customTopicInput: string
  topicAvailability: Record<string, number>
  lowCoverageTopics: string[]
  fallbackNotice: string | null
  onToggleTopic: (topicName: string) => void
  onSelectAll: () => void
  onClear: () => void
  onCustomTopicInputChange: (value: string) => void
  onAddCustomTopic: () => void
  onRemoveCustomTopic: (topicName: string) => void
}

function availabilityStyle(count: number): { bar: string; text: string } {
  if (count >= 9) return { bar: 'bg-emerald-500', text: 'text-emerald-700' }
  if (count >= 5) return { bar: 'bg-amber-500', text: 'text-amber-700' }
  return { bar: 'bg-rose-500', text: 'text-rose-700' }
}

export function TopicSelector({
  customTopicInput,
  customTopics,
  fallbackNotice,
  lowCoverageTopics,
  onAddCustomTopic,
  onClear,
  onCustomTopicInputChange,
  onRemoveCustomTopic,
  onSelectAll,
  onToggleTopic,
  selectedTopics,
  topicAvailability,
  topics,
}: TopicSelectorProps) {
  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={onSelectAll}
          className="rounded-lg border border-brand-200 bg-brand-50 px-3 py-1.5 text-xs font-semibold text-brand-700 transition hover:bg-brand-100"
        >
          Select All
        </button>
        <button
          type="button"
          onClick={onClear}
          className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-600 transition hover:bg-slate-50"
        >
          Clear Selection
        </button>
        <span className="text-xs text-slate-500">{selectedTopics.length} selected</span>
      </div>

      <div className="max-h-[320px] space-y-2 overflow-y-auto rounded-2xl border border-slate-200 bg-slate-50/70 p-3">
        {topics.map((topic) => {
          const checked = selectedTopics.includes(topic.name)
          const available = topicAvailability[topic.name] ?? 0
          const percent = Math.max(8, Math.min(100, Math.round((available / 12) * 100)))
          const tone = availabilityStyle(available)
          return (
            <label
              key={topic.name}
              className="flex items-start justify-between gap-3 rounded-xl border border-transparent bg-white px-3 py-2.5 transition hover:border-brand-200"
            >
              <span className="grid flex-1 gap-2">
                <span className="flex items-start gap-2">
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={() => onToggleTopic(topic.name)}
                  className="mt-1 h-4 w-4 rounded border-slate-300 text-brand-600 focus:ring-brand-400"
                />
                <span className="text-sm text-slate-700">{topic.name}</span>
                </span>
                {checked && (
                  <span className="grid gap-1 pl-6">
                    <span className="h-1.5 w-full overflow-hidden rounded-full bg-slate-200">
                      <span className={`block h-full ${tone.bar}`} style={{ width: `${percent}%` }} />
                    </span>
                    <span className={`text-xs ${tone.text}`}>{available} questions available</span>
                  </span>
                )}
              </span>
              <span className="flex shrink-0 items-center gap-1">
                {topic.frequent && (
                  <span className="rounded-full bg-blue-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-blue-700">
                    Frequently Asked
                  </span>
                )}
                {topic.highWeightage && (
                  <span className="rounded-full bg-indigo-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-indigo-700">
                    High Weightage
                  </span>
                )}
              </span>
            </label>
          )
        })}
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-4">
        <h3 className="text-sm font-semibold text-slate-900">Custom Topics</h3>
        <p className="mt-1 text-xs text-slate-600">Add topics that are not in the predefined checklist.</p>

        <div className="mt-3 flex flex-wrap items-center gap-2">
          {customTopics.map((topic) => (
            <span key={topic} className="inline-flex items-center gap-1 rounded-full border border-brand-200 bg-brand-50 px-2.5 py-1 text-xs text-brand-800">
              {topic}
              <button
                type="button"
                onClick={() => onRemoveCustomTopic(topic)}
                className="rounded-full px-1 text-brand-700 transition hover:bg-brand-100"
                aria-label={`Remove ${topic}`}
              >
                x
              </button>
            </span>
          ))}
          <input
            type="text"
            value={customTopicInput}
            onChange={(event) => onCustomTopicInputChange(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter') {
                event.preventDefault()
                onAddCustomTopic()
              }
            }}
            placeholder="Add topic +"
            className="min-w-[180px] flex-1 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm outline-none ring-brand-300 focus:border-brand-400 focus:ring"
          />
          <button
            type="button"
            onClick={onAddCustomTopic}
            className="rounded-lg border border-brand-200 bg-brand-50 px-3 py-2 text-xs font-semibold text-brand-700 transition hover:bg-brand-100"
          >
            Add
          </button>
        </div>
      </div>

      {lowCoverageTopics.length > 0 && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          <p className="font-semibold">Few questions available for:</p>
          <ul className="mt-1 list-disc pl-5 text-xs">
            {lowCoverageTopics.map((topic) => (
              <li key={topic}>{topic}</li>
            ))}
          </ul>
          <p className="mt-2 text-xs">Some topics have limited historical data. The system will supplement with related questions.</p>
        </div>
      )}

      {fallbackNotice && <div className="rounded-xl border border-blue-200 bg-blue-50 px-4 py-3 text-xs text-blue-900">{fallbackNotice}</div>}
    </div>
  )
}
