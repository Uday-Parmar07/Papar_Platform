interface NavbarProps {
  onStart: () => void
}

export function Navbar({ onStart }: NavbarProps) {
  return (
    <nav className="sticky top-0 z-40 border-b border-blue-100/70 bg-white/90 backdrop-blur-md">
      <div className="mx-auto flex w-full max-w-7xl items-center justify-between px-4 py-3 sm:px-6 lg:px-8">
        <button
          onClick={onStart}
          className="text-left text-sm font-semibold tracking-tight text-slate-900 transition hover:text-brand-700 sm:text-base"
        >
          AI Exam Paper Predictor
        </button>
        <div className="flex items-center gap-4 text-xs font-medium text-slate-600 sm:gap-6 sm:text-sm">
          <a href="#about" className="transition hover:text-brand-700">
            About
          </a>
          <a href="https://github.com" target="_blank" rel="noreferrer noopener" className="transition hover:text-brand-700">
            GitHub
          </a>
          <a href="#help" className="transition hover:text-brand-700">
            Help
          </a>
        </div>
      </div>
    </nav>
  )
}
