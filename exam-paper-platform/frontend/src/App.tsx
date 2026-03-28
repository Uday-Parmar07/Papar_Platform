import { useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import './App.css'
import { fetchSubjects, fetchTopics, generatePaper } from './services/api'
import type { GeneratePaperQuestion } from './types'

function App() {
  const [subjects, setSubjects] = useState<string[]>([])
  const [topics, setTopics] = useState<string[]>([])
  const [selectedSubject, setSelectedSubject] = useState('')
  const [selectedTopics, setSelectedTopics] = useState<string[]>([])
  const [cutoffYear, setCutoffYear] = useState<number>(2023)
  const [numQuestions, setNumQuestions] = useState<number>(10)
  const [generatedQuestions, setGeneratedQuestions] = useState<GeneratePaperQuestion[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    async function loadSubjects() {
      try {
        const data = await fetchSubjects()
        setSubjects(data.subjects)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unable to load subjects')
      }
    }
    void loadSubjects()
  }, [])

  useEffect(() => {
    async function loadTopics() {
      if (!selectedSubject) {
        setTopics([])
        setSelectedTopics([])
        return
      }
      try {
        const data = await fetchTopics(selectedSubject)
        setTopics(data.topics)
        setSelectedTopics([])
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unable to load topics')
      }
    }
    void loadTopics()
  }, [selectedSubject])

  const selectedTopicSet = useMemo(() => new Set(selectedTopics), [selectedTopics])

  function onTopicToggle(topic: string) {
    setSelectedTopics((prev) => {
      if (prev.includes(topic)) {
        return prev.filter((item) => item !== topic)
      }
      return [...prev, topic]
    })
  }

  async function onGenerate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')

    if (!selectedSubject) {
      setError('Please select a subject')
      return
    }

    if (selectedTopics.length === 0) {
      setError('Please choose at least one topic')
      return
    }

    setLoading(true)
    try {
      const response = await generatePaper({
        subject: selectedSubject,
        topics: selectedTopics,
        cutoff_year: cutoffYear,
        num_questions: numQuestions,
      })
      setGeneratedQuestions(response.questions)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Paper generation failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page">
      <main className="container">
        <h1>AI Exam Paper Generator</h1>

        <section className="card">
          <form onSubmit={onGenerate}>
            <label>
              Subject
              <select value={selectedSubject} onChange={(e) => setSelectedSubject(e.target.value)}>
                <option value="">Select a subject</option>
                {subjects.map((subject) => (
                  <option key={subject} value={subject}>
                    {subject}
                  </option>
                ))}
              </select>
            </label>

            <label>
              Topics
              <div className="topics-grid">
                {topics.map((topic) => (
                  <button
                    type="button"
                    key={topic}
                    className={selectedTopicSet.has(topic) ? 'topic-chip active' : 'topic-chip'}
                    onClick={() => onTopicToggle(topic)}
                  >
                    {topic}
                  </button>
                ))}
              </div>
            </label>

            <label>
              Cutoff Year
              <input
                type="number"
                min={1990}
                max={2100}
                value={cutoffYear}
                onChange={(e) => setCutoffYear(Number(e.target.value))}
              />
            </label>

            <label>
              Number of Questions
              <input
                type="number"
                min={1}
                max={100}
                value={numQuestions}
                onChange={(e) => setNumQuestions(Number(e.target.value))}
              />
            </label>

            <button type="submit" className="generate-button" disabled={loading}>
              {loading ? 'Generating...' : 'Generate Paper'}
            </button>
          </form>
          {error ? <p className="error">{error}</p> : null}
        </section>

        <section className="card">
          <h2>Predicted Exam Paper</h2>
          <p className="subject-line">Subject: {selectedSubject || 'Not selected'}</p>
          {generatedQuestions.length === 0 ? (
            <p className="placeholder">Generated questions will appear here.</p>
          ) : (
            <ol className="question-list">
              {generatedQuestions.map((item, index) => (
                <li key={`${item.topic}-${index}`}>
                  <p>{item.question}</p>
                  <span>{item.topic}</span>
                </li>
              ))}
            </ol>
          )}
        </section>
      </main>
    </div>
  )
}

export default App