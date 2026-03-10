export interface Branch {
  id: string
  name: string
  description: string
}

interface BranchSelectorProps {
  branches: Branch[]
  selectedBranch: string | null
  onSelect: (branchId: string) => void
}

export function BranchSelector({ branches, selectedBranch, onSelect }: BranchSelectorProps) {
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {branches.map((branch) => {
        const selected = selectedBranch === branch.id
        return (
          <button
            key={branch.id}
            type="button"
            onClick={() => onSelect(branch.id)}
            className={[
              'rounded-2xl border px-4 py-4 text-left transition',
              selected
                ? 'border-brand-500 bg-brand-50 shadow-md shadow-blue-100'
                : 'border-slate-200 bg-white hover:border-brand-300 hover:bg-brand-50/40',
            ].join(' ')}
          >
            <h3 className="text-sm font-semibold text-slate-900">{branch.name}</h3>
            <p className="mt-1 text-xs leading-relaxed text-slate-600">{branch.description}</p>
          </button>
        )
      })}
    </div>
  )
}
