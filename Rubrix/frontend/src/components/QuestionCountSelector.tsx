import { Plus, Minus } from './icons'

interface QuestionCountSelectorProps {
  count: number
  min?: number
  max?: number
  onChange: (count: number) => void
}

export default function QuestionCountSelector({
  count,
  min = 1,
  max = 100,
  onChange,
}: QuestionCountSelectorProps) {
  const handleDecrement = () => {
    if (count > min) {
      onChange(count - 1)
    }
  }

  const handleIncrement = () => {
    if (count < max) {
      onChange(count + 1)
    }
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = parseInt(e.target.value, 10)
    if (!isNaN(value)) {
      onChange(Math.max(min, Math.min(max, value)))
    }
  }

  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium text-gray-700">
        Number of Questions
      </label>
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={handleDecrement}
          disabled={count <= min}
          className={`p-3 rounded-xl border transition-all ${
            count <= min
              ? 'border-gray-200 text-gray-300 cursor-not-allowed'
              : 'border-gray-200 text-gray-600 hover:border-indigo-300 hover:bg-indigo-50 hover:text-indigo-600 active:scale-95'
          }`}
        >
          <Minus className="w-5 h-5" />
        </button>

        <div className="relative">
          <input
            type="number"
            value={count}
            onChange={handleInputChange}
            min={min}
            max={max}
            className="w-24 text-center py-3 px-4 text-xl font-bold text-gray-800 border border-gray-200 rounded-xl focus:outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
          />
        </div>

        <button
          type="button"
          onClick={handleIncrement}
          disabled={count >= max}
          className={`p-3 rounded-xl border transition-all ${
            count >= max
              ? 'border-gray-200 text-gray-300 cursor-not-allowed'
              : 'border-gray-200 text-gray-600 hover:border-indigo-300 hover:bg-indigo-50 hover:text-indigo-600 active:scale-95'
          }`}
        >
          <Plus className="w-5 h-5" />
        </button>

        <span className="text-sm text-gray-500 ml-2">
          questions
        </span>
      </div>
      <p className="text-xs text-gray-400">
        Min {min} • Max {max}
      </p>
    </div>
  )
}
