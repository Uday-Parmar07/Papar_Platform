interface YearRangeSliderProps {
  minYear: number
  maxYear: number
  fromYear: number
  toYear: number
  onFromChange: (year: number) => void
  onToChange: (year: number) => void
}

export function YearRangeSlider({ maxYear, minYear, fromYear, toYear, onFromChange, onToChange }: YearRangeSliderProps) {
  return (
    <div className="grid gap-6">
      <div className="relative pt-4">
        <div className="h-2 rounded-full bg-gradient-to-r from-brand-500/70 to-indigo-500/70" />

        <input
          type="range"
          title="From year"
          aria-label="From year"
          min={minYear}
          max={maxYear}
          value={fromYear}
          onChange={(event) => onFromChange(Math.min(Number(event.target.value), toYear - 1))}
          className="pointer-events-none absolute left-0 top-2 h-6 w-full appearance-none bg-transparent [&::-webkit-slider-thumb]:pointer-events-auto [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-brand-600"
        />

        <input
          type="range"
          title="To year"
          aria-label="To year"
          min={minYear}
          max={maxYear}
          value={toYear}
          onChange={(event) => onToChange(Math.max(Number(event.target.value), fromYear + 1))}
          className="pointer-events-none absolute left-0 top-2 h-6 w-full appearance-none bg-transparent [&::-webkit-slider-thumb]:pointer-events-auto [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-indigo-600"
        />
      </div>

      <div className="grid grid-cols-2 gap-3 text-center">
        <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
          <p className="text-xs uppercase tracking-wide text-slate-500">From Year</p>
          <p className="text-xl font-semibold text-slate-800">{fromYear}</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
          <p className="text-xs uppercase tracking-wide text-slate-500">To Year</p>
          <p className="text-xl font-semibold text-slate-800">{toYear}</p>
        </div>
      </div>
    </div>
  )
}
