interface StepperProps {
  steps: string[]
  currentStep: number
}

export function Stepper({ steps, currentStep }: StepperProps) {
  return (
    <div className="grid gap-3">
      <div className="flex items-center justify-between gap-2">
        {steps.map((step, index) => {
          const active = index === currentStep
          const completed = index < currentStep

          return (
            <div key={step} className="flex min-w-0 flex-1 items-center gap-2">
              <div
                className={[
                  'flex h-8 w-8 shrink-0 items-center justify-center rounded-full border text-xs font-semibold transition',
                  completed ? 'border-brand-600 bg-brand-600 text-white' : '',
                  active ? 'border-brand-600 bg-brand-50 text-brand-700' : '',
                  !active && !completed ? 'border-slate-200 bg-white text-slate-500' : '',
                ].join(' ')}
              >
                {index + 1}
              </div>
              <span
                className={[
                  'hidden truncate text-xs font-medium sm:block',
                  active ? 'text-slate-900' : 'text-slate-500',
                ].join(' ')}
              >
                {step}
              </span>
              {index < steps.length - 1 && <div className="h-px flex-1 bg-slate-200" />}
            </div>
          )
        })}
      </div>
      <p className="text-xs text-slate-500">
        Step {currentStep + 1} of {steps.length}: <span className="font-semibold text-slate-700">{steps[currentStep]}</span>
      </p>
    </div>
  )
}
