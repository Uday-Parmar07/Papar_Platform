import { useEffect, useMemo, useState } from 'react'
import './App.css'
import { QuestionTable } from './components/QuestionTable'
import { downloadPdf, fetchSubjects, fetchTopics, generateAnswers, generateExam, verifyQuestions } from './services/api'
import type { AnswerResult, Question, SubjectOption, VerifyResult } from './types'

function App() {
  const [totalQuestions, setTotalQuestions] = useState(20)
  const [cutoffYear, setCutoffYear] = useState(2019)
  const [subjects, setSubjects] = useState<SubjectOption[]>([])
  const [subjectId, setSubjectId] = useState('')
  const [subjectName, setSubjectName] = useState('')
  const [subjectsLoading, setSubjectsLoading] = useState(true)
  const [topics, setTopics] = useState<string[]>([])
  const [topicsMode, setTopicsMode] = useState<'all' | 'custom'>('all')
  const [selectedTopics, setSelectedTopics] = useState<string[]>([])
  const [topicsLoading, setTopicsLoading] = useState(false)
  const [questions, setQuestions] = useState<Question[]>([])
  const [distribution, setDistribution] = useState<Record<string, number> | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [verifyLoading, setVerifyLoading] = useState(false)
  const [pdfLoading, setPdfLoading] = useState(false)
  const [verification, setVerification] = useState<VerifyResult[] | undefined>(undefined)
  const [verificationSummary, setVerificationSummary] = useState<{ valid: number; invalid: number } | null>(null)
  const [answerLoading, setAnswerLoading] = useState(false)
  const [answers, setAnswers] = useState<AnswerResult[]>([])

  const hasQuestions = questions.length > 0
  const distributionItems = useMemo(() => {
    if (!distribution) return []
    return Object.entries(distribution)
  }, [distribution])

  const topicSummary = useMemo(() => {
    if (topics.length === 0) {
      return 'Topics will appear once data is ingested.'
    }

    if (topicsMode === 'all' || selectedTopics.length === topics.length) {
      return `All ${topics.length} topics selected`
    }

    if (selectedTopics.length === 0) {
      return 'No topics selected'
    }

    const preview = selectedTopics.slice(0, 3).join(', ')
    const remainder = selectedTopics.length - 3
    return remainder > 0 ? `${preview} (+${remainder} more)` : preview
  }, [topicsMode, selectedTopics, topics])

  useEffect(() => {
    let active = true

    async function loadSubjects() {
      try {
        const response = await fetchSubjects()
        if (!active) return
        setSubjects(response.subjects)
        if (response.subjects.length > 0) {
          setSubjectId((current) => (current ? current : response.subjects[0].id))
          setSubjectName((current) => (current ? current : response.subjects[0].name))
        }
      } catch (err) {
        if (!active) return
        const message = err instanceof Error ? err.message : 'Unable to load subjects'
        setError(message)
      } finally {
        if (active) setSubjectsLoading(false)
      }
    }

    loadSubjects()
    return () => {
      active = false
    }
  }, [])

  useEffect(() => {
    let active = true

    async function loadTopics() {
      if (!subjectId) {
        setTopics([])
        setSelectedTopics([])
        return
      }

      setTopicsLoading(true)
      setTopics([])
      setSelectedTopics([])
      setTopicsMode('all')

      try {
        const response = await fetchTopics(subjectId)
        if (!active) return
        setTopics(response.topics)
      } catch (err) {
        if (!active) return
        const message = err instanceof Error ? err.message : 'Unable to load topics'
        setError(message)
      } finally {
        if (active) setTopicsLoading(false)
      }
    }

    loadTopics()

    return () => {
      active = false
    }
  }, [subjectId])

  const handleGenerate = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setLoading(true)
    setError(null)
    setVerification(undefined)
    setVerificationSummary(null)
    setAnswers([])

    if (!subjectId) {
      setError('Please select a subject before generating questions')
      setLoading(false)
      return
    }

    if (topicsMode === 'custom' && selectedTopics.length === 0) {
      setError('Please choose at least one topic or switch back to all topics')
      setLoading(false)
      return
    }

    const payloadTopics =
      topicsMode === 'custom' && selectedTopics.length > 0 && selectedTopics.length !== topics.length
        ? selectedTopics
        : undefined

    try {
      const response = await generateExam({
        subject: subjectId,
        total_questions: totalQuestions,
        cutoff_year: cutoffYear,
        topics: payloadTopics,
      })

      setQuestions(response.questions)
      setDistribution(response.distribution)
      if (response.subject_id) {
        setSubjectId(response.subject_id)
      }
      if (response.subject_name) {
        setSubjectName(response.subject_name)
      }
      if (Array.isArray(response.topics)) {
        setSelectedTopics([...response.topics])
        if (response.topics.length === topics.length) {
          setTopicsMode('all')
        } else {
          setTopicsMode('custom')
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to generate questions')
      setQuestions([])
      setDistribution(null)
    } finally {
      setLoading(false)
    }
  }

  const handleVerify = async () => {
    setVerifyLoading(true)
    setError(null)

    try {
      const response = await verifyQuestions(questions)
      setVerification(response.results)
      setVerificationSummary({ valid: response.valid, invalid: response.invalid })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Verification failed')
    } finally {
      setVerifyLoading(false)
    }
  }

  const handleGenerateAnswers = async () => {
    if (questions.length === 0) return
    setAnswerLoading(true)
    setError(null)

    try {
      const namespace = subjectName?.trim().length ? subjectName : 'Electrical Engineering'
      const response = await generateAnswers({ questions, namespace })
      setAnswers(response.answers)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to generate answers')
    } finally {
      setAnswerLoading(false)
    }
  }

  const handleDownloadPdf = async () => {
    setPdfLoading(true)
    setError(null)

    try {
      const blob = await downloadPdf({
        questions,
        title: `${subjectName || 'Practice'} Paper (${totalQuestions} Questions)`
      })
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = 'exam-paper.pdf'
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to export PDF')
    } finally {
      setPdfLoading(false)
    }
  }

  return (
    <div className="app">
      <header className="hero">
        <h1>Paper Builder</h1>
        <p>Create a balanced set of questions, review them instantly, and export a polished PDF ready for distribution.</p>
      </header>

      <main className="layout">
        <section className="card controls">
          <div className="card-head">
            <h2>Plan your paper</h2>
            <span className="hint">Adjust the knobs and generate a fresh set when you are ready.</span>
          </div>
          <form className="form" onSubmit={handleGenerate}>
            <label className="field">
              <span>Subject</span>
              <select
                value={subjectId}
                onChange={(event) => {
                  const nextId = event.target.value
                  setSubjectId(nextId)
                  const match = subjects.find((option) => option.id === nextId)
                  setSubjectName(match ? match.name : '')
                }}
                disabled={subjectsLoading || loading || subjects.length === 0}
                required
              >
                {subjects.length === 0 ? (
                  <option value="" disabled>
                    {subjectsLoading ? 'Loading subjects…' : 'No subjects available'}
                  </option>
                ) : (
                  subjects.map((option) => (
                    <option key={option.id} value={option.id}>
                      {option.name}
                    </option>
                  ))
                )}
              </select>
            </label>
            <fieldset className="field fieldset">
              <legend>Topics</legend>
              {topicsLoading ? (
                <div className="hint">Loading topics…</div>
              ) : topics.length === 0 ? (
                <div className="hint">No topics found for this subject yet.</div>
              ) : (
                <>
                  <label className="option">
                    <input
                      type="radio"
                      name="topics-mode"
                      value="all"
                      checked={topicsMode === 'all'}
                      onChange={() => {
                        setTopicsMode('all')
                        setSelectedTopics([...topics])
                      }}
                    />
                    <span>All topics ({topics.length})</span>
                  </label>
                  <label className="option">
                    <input
                      type="radio"
                      name="topics-mode"
                      value="custom"
                      checked={topicsMode === 'custom'}
                      onChange={() => {
                        setTopicsMode('custom')
                        setSelectedTopics([...topics])
                      }}
                    />
                    <span>Choose specific topics</span>
                  </label>
                  {topicsMode === 'custom' && (
                    <div className="topic-grid">
                      {topics.map((topic) => {
                        const checked = selectedTopics.includes(topic)
                        return (
                          <label key={topic} className="chip">
                            <input
                              type="checkbox"
                              value={topic}
                              checked={checked}
                              onChange={(event) => {
                                const { checked: isChecked } = event.target
                                setSelectedTopics((prev) => {
                                  if (isChecked) {
                                    return prev.includes(topic) ? prev : [...prev, topic]
                                  }
                                  return prev.filter((value) => value !== topic)
                                })
                              }}
                            />
                            <span>{topic}</span>
                          </label>
                        )
                      })}
                    </div>
                  )}
                </>
              )}
            </fieldset>
            <label className="field">
              <span>Total questions</span>
              <input
                type="number"
                min={1}
                max={120}
                value={totalQuestions}
                onChange={(event) => setTotalQuestions(Number(event.target.value))}
                required
              />
            </label>
            <label className="field">
              <span>Exclude past papers after year</span>
              <input
                type="number"
                min={2000}
                value={cutoffYear}
                onChange={(event) => setCutoffYear(Number(event.target.value))}
                required
              />
            </label>
            <button type="submit" className="primary" disabled={loading || subjects.length === 0}>
              {loading ? 'Generating…' : 'Generate questions'}
            </button>
          </form>

          {subjectName && (
            <div className="selection-summary">
              <span className="summary-title">{subjectName}</span>
              <span className="summary-meta">{topicSummary}</span>
            </div>
          )}

          {distributionItems.length > 0 && (
            <div className="summary-grid">
              {distributionItems.map(([bucket, count]) => (
                <div key={bucket} className="stat">
                  <span className="stat-label">{bucket.replace('_', ' ')}</span>
                  <span className="stat-value">{count}</span>
                </div>
              ))}
            </div>
          )}
        </section>

        {error && <div className="alert">{error}</div>}

        {hasQuestions && (
          <section className="card">
            <div className="card-head">
              <h2>Generated questions</h2>
              <span className="hint">Review each question below, mark issues, and export when satisfied.</span>
            </div>
            <div className="toolbar">
              <div className="toolbar-actions">
                <button onClick={handleGenerateAnswers} className="secondary" disabled={answerLoading}>
                  {answerLoading ? 'Generating answers…' : 'Generate answers'}
                </button>
                <button onClick={handleVerify} className="secondary" disabled={verifyLoading}>
                  {verifyLoading ? 'Checking…' : 'Run quick verification'}
                </button>
                <button onClick={handleDownloadPdf} className="primary" disabled={pdfLoading}>
                  {pdfLoading ? 'Preparing…' : 'Download PDF'}
                </button>
              </div>
              {verificationSummary && (
                <div className="badge-strip">
                  <span className="badge success">{verificationSummary.valid} ready</span>
                  <span className="badge neutral">{verificationSummary.invalid} needs attention</span>
                </div>
              )}
            </div>

            <QuestionTable questions={questions} verification={verification} answers={answers} />
          </section>
        )}
      </main>
    </div>
  )
}

export default App
