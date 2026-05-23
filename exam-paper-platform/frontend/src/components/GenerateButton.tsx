import { Sparkles, Loader } from './icons'

interface GenerateButtonProps {
  onClick: () => void
  loading?: boolean
  disabled?: boolean
}

export default function GenerateButton({
  onClick,
  loading = false,
  disabled = false,
}: GenerateButtonProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled || loading}
      className={`
        relative w-full py-4 px-6 rounded-xl font-semibold text-lg
        transition-all duration-300 transform
        ${
          disabled || loading
            ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
            : 'bg-gradient-to-r from-indigo-600 to-purple-600 text-white shadow-lg shadow-indigo-500/30 hover:shadow-xl hover:shadow-indigo-500/40 hover:-translate-y-0.5 active:translate-y-0 active:shadow-md'
        }
      `}
    >
      {/* Gradient Overlay on Hover */}
      {!disabled && !loading && (
        <div className="absolute inset-0 rounded-xl bg-gradient-to-r from-indigo-500 to-purple-500 opacity-0 hover:opacity-100 transition-opacity duration-300" />
      )}

      {/* Button Content */}
      <span className="relative flex items-center justify-center gap-3">
        {loading ? (
          <>
            <Loader className="w-6 h-6" />
            <span>Generating Paper...</span>
          </>
        ) : (
          <>
            <span>Generate Full Question Paper</span>
            <Sparkles className="w-6 h-6" />
          </>
        )}
      </span>
    </button>
  )
}
