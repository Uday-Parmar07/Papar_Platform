import { useEffect, useMemo, useState } from 'react'
import './App.css'
import { QuestionTable } from './components/QuestionTable'
import { downloadPdf, fetchSubjects, generateExam, verifyQuestions } from './services/api'
import type { Question, VerifyResult } from './types'

function App() {
  const [totalQuestions, setTotalQuestions] = useState(20)
  const [cutoffYear, setCutoffYear] = useState(2019)
  const [subjects, setSubjects] = useState<string[]>([])
  const [subject, setSubject] = useState('')
  const [subjectsLoading, setSubjectsLoading] = useState(true)
  const [questions, setQuestions] = useState<Question[]>([])
  const [distribution, setDistribution] = useState<Record<string, number> | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [verifyLoading, setVerifyLoading] = useState(false)
  const [pdfLoading, setPdfLoading] = useState(false)
  const [verification, setVerification] = useState<VerifyResult[] | undefined>(undefined)
  const [verificationSummary, setVerificationSummary] = useState<{ valid: number; invalid: number } | null>(null)

  const hasQuestions = questions.length > 0
  const distributionItems = useMemo(() => {
    if (!distribution) return []
    return Object.entries(distribution)
  }, [distribution])

  useEffect(() => {
    let active = true

    async function loadSubjects() {
      try {
        const response = await fetchSubjects()
        if (!active) return
        setSubjects(response.subjects)
        if (response.subjects.length > 0) {
          setSubject((current) => (current ? current : response.subjects[0]))
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

  const handleGenerate = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setLoading(true)
    setError(null)
    setVerification(undefined)
    setVerificationSummary(null)

    if (!subject) {
      setError('Please select a subject before generating questions')
      setLoading(false)
      return
    }

    try {
      const response = await generateExam({
        subject,
        total_questions: totalQuestions,
        cutoff_year: cutoffYear,
      })

      setQuestions(response.questions)
      setDistribution(response.distribution)
      if (response.subject) {
        setSubject(response.subject)
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

  const handleDownloadPdf = async () => {
    setPdfLoading(true)
    setError(null)

    try {
      const blob = await downloadPdf({
        questions,
        title: `${subject || 'Practice'} Paper (${totalQuestions} Questions)`,
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
                value={subject}
                onChange={(event) => setSubject(event.target.value)}
                disabled={subjectsLoading || loading || subjects.length === 0}
                required
              >
                {subjects.length === 0 ? (
                  <option value="" disabled>
                    {subjectsLoading ? 'Loading subjects…' : 'No subjects available'}
                  </option>
                ) : (
                  subjects.map((subjectName) => (
                    <option key={subjectName} value={subjectName}>
                      {subjectName}
                    </option>
                  ))
                )}
              </select>
            </label>
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

            <QuestionTable questions={questions} verification={verification} />
          </section>
        )}
      </main>
    </div>
  )
}

export default App
