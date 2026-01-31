import type { AnswerResult, Question, VerifyResult } from '../types'

interface Props {
  questions: Question[]
  verification?: VerifyResult[]
  answers?: AnswerResult[]
}

export function QuestionTable({ questions, verification, answers }: Props) {
  const verdict = (index: number) => verification?.[index]
  const answerFor = (index: number) => answers?.[index]

  return (
    <ul className="question-list">
      {questions.map((question, index) => {
        const check = verdict(index)
        const answer = answerFor(index)
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
            <div className="question-tags">
              <span className="tag">{question.concept}</span>
              <span className="tag subtle">{question.difficulty}</span>
            </div>
            <p className="question-text">{question.question}</p>
            {answer && (
              <div className="answer-block">
                <span className="answer-label">Answer</span>
                <p className="answer-text">{answer.answer}</p>
                <div className="answer-foot">
                  <span className={answer.context_retrieved ? 'badge success' : 'badge neutral'}>
                    {answer.context_retrieved ? 'Context applied' : 'Generated without context'}
                  </span>
                </div>
              </div>
            )}
          </li>
        )
      })}
    </ul>
  )
}
