import type { Question, VerifyResult } from '../types'

interface Props {
  questions: Question[]
  verification?: VerifyResult[]
}

export function QuestionTable({ questions, verification }: Props) {
  const verdict = (index: number) => verification?.[index]

  return (
    <ul className="question-list">
      {questions.map((question, index) => {
        const check = verdict(index)
        return (
          <li key={index} className={check?.valid === false ? 'question-item invalid' : 'question-item'}>
            <div className="question-meta">
              <span className="question-number">{index + 1}</span>
              {check && (
                <span className={check.valid ? 'badge success' : 'badge danger'}>
                  {check.valid ? 'Ready' : check.reason}
                </span>
              )}
            </div>
            <p className="question-text">{question.question}</p>
          </li>
        )
      })}
    </ul>
  )
}
