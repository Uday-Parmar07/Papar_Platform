interface SubjectSelectorProps {
  subjects: string[]
  selectedSubject: string | null
  search: string
  onSearch: (value: string) => void
  onSelect: (subject: string) => void
}

export function SubjectSelector({ subjects, selectedSubject, search, onSearch, onSelect }: SubjectSelectorProps) {
  return (
    <div className="grid gap-4">
      <input
        type="search"
        value={search}
        onChange={(event) => onSearch(event.target.value)}
        placeholder="Search subjects..."
        className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-2.5 text-sm outline-none ring-brand-300 transition focus:border-brand-400 focus:ring"
      />
      <div className="grid max-h-[320px] gap-3 overflow-y-auto pr-1 sm:grid-cols-2">
        {subjects.map((subject) => {
          const selected = subject === selectedSubject
          return (
            <button
              key={subject}
              type="button"
              onClick={() => onSelect(subject)}
              className={[
                'rounded-2xl border px-4 py-3 text-left text-sm font-medium transition',
                selected
                  ? 'border-brand-500 bg-brand-50 text-brand-800'
                  : 'border-slate-200 bg-white text-slate-700 hover:border-brand-300 hover:bg-brand-50/30',
              ].join(' ')}
            >
              {subject}
            </button>
          )
        })}
      </div>
    </div>
  )
}
