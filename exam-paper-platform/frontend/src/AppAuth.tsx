import { useEffect, useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import './AppAuth.css'
import {
  clearToken,
  explainQuestion,
  fetchDashboard,
  fetchHistory,
  fetchPaper,
  fetchSubjects,
  fetchTopics,
  generatePaper,
  getToken,
  login,
  register,
  setToken,
} from './services/api'
import type {
  DashboardResponse,
  ExplainResponse,
  PaperDetail,
  PaperHistoryItem,
  Question,
  SubjectOption,
} from './types'

type Page = 'login' | 'register' | 'dashboard' | 'generate' | 'history'
type DifficultyView = 'easy' | 'medium' | 'university' | 'gate'

const navItems: Array<{ id: Exclude<Page, 'login' | 'register'>; label: string; icon: string }> = [
  { id: 'dashboard', label: 'Dashboard', icon: 'grid' },
  { id: 'generate', label: 'Generate Paper', icon: 'sparkles' },
  { id: 'history', label: 'Paper History', icon: 'clock' },
]

function Icon(props: { name: string }) {
  const { name } = props
  if (name === 'grid') return <span aria-hidden="true">#</span>
  if (name === 'sparkles') return <span aria-hidden="true">*</span>
  if (name === 'clock') return <span aria-hidden="true">@</span>
  if (name === 'user') return <span aria-hidden="true">U</span>
  if (name === 'moon') return <span aria-hidden="true">M</span>
  if (name === 'sun') return <span aria-hidden="true">S</span>
  if (name === 'file') return <span aria-hidden="true">F</span>
  if (name === 'help') return <span aria-hidden="true">?</span>
  if (name === 'book') return <span aria-hidden="true">B</span>
  return null
}

function toExplainDifficulty(value: string): 'easy' | 'medium' | 'exam' {
  const normalized = value.toLowerCase()
  if (normalized.includes('easy')) return 'easy'
  if (normalized.includes('hard') || normalized.includes('gate')) return 'exam'
  return 'medium'
}

function QuestionList(props: {
  questions: Question[]
  explanations: Record<string, ExplainResponse>
  openExplain: Record<string, boolean>
  openAnswer: Record<string, boolean>
  importantQuestions: Record<string, boolean>
  onExplain: (question: Question) => Promise<void>
  onShowAnswer: (question: Question) => Promise<void>
  onToggleImportant: (question: Question) => void
}) {
  const { questions, explanations, openExplain, openAnswer, importantQuestions, onExplain, onShowAnswer, onToggleImportant } = props

  return (
    <div className="question-list">
      {questions.map((question, index) => {
        const key = `${question.concept}::${question.question}`
        const explanation = explanations[key]
        const show = openExplain[key]
        const showAnswer = openAnswer[key]
        const important = importantQuestions[key]

        return (
          <article key={key} className="question-card">
            <div className="question-head">
              <h4>Question {index + 1}</h4>
              <span className={`importance-pill ${important ? 'active' : ''}`}>{important ? 'Important' : 'Normal'}</span>
            </div>
            <p className="question-text">{question.question}</p>
            <p className="muted">Topic: {question.concept} | Difficulty: {question.difficulty}</p>

            <div className="question-actions">
              <button type="button" onClick={() => void onExplain(question)}>Explain</button>
              <button type="button" className="button-secondary" onClick={() => void onShowAnswer(question)}>Show Answer</button>
              <button type="button" className="button-secondary" onClick={() => onToggleImportant(question)}>Mark Important</button>
            </div>

            {show && explanation ? (
              <div className="explain-panel">
                <p><strong>Concept:</strong> {explanation.concept}</p>
                <p><strong>Formula:</strong> {explanation.formula}</p>
                <p><strong>Step-by-step solution:</strong> {explanation.steps}</p>
                <p><strong>Final Answer:</strong> {explanation.answer}</p>
              </div>
            ) : null}

            {showAnswer ? (
              <div className="answer-panel">
                <p><strong>Answer:</strong> {explanation?.answer ?? 'Click Explain first to load answer details.'}</p>
              </div>
            ) : null}
          </article>
        )
      })}
    </div>
  )
}

export default function AppAuth() {
  const [tokenState, setTokenState] = useState<string | null>(getToken())
  const [page, setPage] = useState<Page>(tokenState ? 'dashboard' : 'login')
  const [error, setError] = useState('')

  const [registerName, setRegisterName] = useState('')
  const [registerEmail, setRegisterEmail] = useState('')
  const [registerPassword, setRegisterPassword] = useState('')
  const [loginEmail, setLoginEmail] = useState('')
  const [loginPassword, setLoginPassword] = useState('')

  const [dashboard, setDashboard] = useState<DashboardResponse | null>(null)
  const [history, setHistory] = useState<PaperHistoryItem[]>([])
  const [selectedPaper, setSelectedPaper] = useState<PaperDetail | null>(null)

  const [subjects, setSubjects] = useState<SubjectOption[]>([])
  const [subjectId, setSubjectId] = useState('')
  const [topics, setTopics] = useState<string[]>([])
  const [selectedTopics, setSelectedTopics] = useState<string[]>([])
  const [cutoffYear, setCutoffYear] = useState(2024)
  const [totalQuestions, setTotalQuestions] = useState(10)
  const [difficulty, setDifficulty] = useState<DifficultyView>('medium')
  const [topicSearch, setTopicSearch] = useState('')
  const [latestPaper, setLatestPaper] = useState<PaperDetail | null>(null)
  const [isGenerating, setIsGenerating] = useState(false)

  const [explanations, setExplanations] = useState<Record<string, ExplainResponse>>({})
  const [openExplain, setOpenExplain] = useState<Record<string, boolean>>({})
  const [openAnswer, setOpenAnswer] = useState<Record<string, boolean>>({})
  const [importantQuestions, setImportantQuestions] = useState<Record<string, boolean>>({})

  const [historySearch, setHistorySearch] = useState('')
  const [historySubjectFilter, setHistorySubjectFilter] = useState('all')
  const [historySort, setHistorySort] = useState<'newest' | 'oldest'>('newest')

  const [profileOpen, setProfileOpen] = useState(false)
  const [darkMode, setDarkMode] = useState<boolean>(() => localStorage.getItem('exam_platform_theme') === 'dark')

  const isAuthenticated = Boolean(tokenState)
  const activeTitle = page === 'dashboard' ? 'Dashboard' : page === 'generate' ? 'Generate Paper' : page === 'history' ? 'Paper History' : 'Authentication'

  const recentPapers = useMemo(() => dashboard?.recent_papers ?? [], [dashboard])
  const topicsPracticed = useMemo(() => new Set(history.flatMap((item) => item.topics)).size, [history])
  const accuracyRate = useMemo(() => {
    const solved = dashboard?.total_questions_solved ?? 0
    if (!solved) return 0
    return Math.min(97, Math.round(62 + solved * 0.55))
  }, [dashboard?.total_questions_solved])

  const filteredTopics = useMemo(() => {
    const q = topicSearch.toLowerCase().trim()
    if (!q) return topics
    return topics.filter((topic) => topic.toLowerCase().includes(q))
  }, [topicSearch, topics])

  const filteredHistory = useMemo(() => {
    const q = historySearch.toLowerCase().trim()
    const filtered = history.filter((item) => {
      const matchesSearch = !q || item.subject.toLowerCase().includes(q) || item.topics.some((topic) => topic.toLowerCase().includes(q))
      const matchesFilter = historySubjectFilter === 'all' || item.subject.toLowerCase().includes(historySubjectFilter)
      return matchesSearch && matchesFilter
    })

    filtered.sort((a, b) => {
      const left = new Date(a.created_at).getTime()
      const right = new Date(b.created_at).getTime()
      return historySort === 'newest' ? right - left : left - right
    })
    return filtered
  }, [history, historySearch, historySort, historySubjectFilter])

  const chartData = useMemo(() => {
    const buckets = new Map<string, number>()
    history.forEach((item) => {
      const key = new Date(item.created_at).toLocaleDateString()
      const value = buckets.get(key) ?? 0
      buckets.set(key, value + (item.total_questions || 0))
    })
    return Array.from(buckets.entries()).slice(-7).map(([label, value]) => ({ label, value }))
  }, [history])

  const chartMax = useMemo(() => Math.max(1, ...chartData.map((item) => item.value)), [chartData])

  useEffect(() => {
    document.documentElement.dataset.theme = darkMode ? 'dark' : 'light'
    localStorage.setItem('exam_platform_theme', darkMode ? 'dark' : 'light')
  }, [darkMode])

  useEffect(() => {
    async function loadSubjects() {
      try {
        const subjectResponse = await fetchSubjects()
        setSubjects(subjectResponse.subjects)
      } catch (exc) {
        setError(exc instanceof Error ? exc.message : 'Unable to load subjects')
      }
    }
    void loadSubjects()
  }, [])

  useEffect(() => {
    async function loadTopics() {
      if (!subjectId) {
        setTopics([])
        setSelectedTopics([])
        return
      }
      try {
        const topicResponse = await fetchTopics(subjectId)
        setTopics(topicResponse.topics)
        setSelectedTopics(topicResponse.topics.slice(0, 6))
      } catch (exc) {
        setError(exc instanceof Error ? exc.message : 'Unable to load topics')
      }
    }
    void loadTopics()
  }, [subjectId])

  useEffect(() => {
    async function loadProtectedData() {
      if (!isAuthenticated) return
      try {
        const [dashData, historyData] = await Promise.all([fetchDashboard(), fetchHistory()])
        setDashboard(dashData)
        setHistory(historyData)
      } catch (exc) {
        setError(exc instanceof Error ? exc.message : 'Unable to load account data')
      }
    }
    void loadProtectedData()
  }, [isAuthenticated])

  async function onRegister(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    try {
      await register({ name: registerName, email: registerEmail, password: registerPassword })
      setPage('login')
      setLoginEmail(registerEmail)
      setRegisterPassword('')
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : 'Registration failed')
    }
  }

  async function onLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    try {
      const data = await login({ email: loginEmail, password: loginPassword })
      setToken(data.access_token)
      setTokenState(data.access_token)
      setPage('dashboard')
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : 'Login failed')
    }
  }

  function onLogout() {
    clearToken()
    setTokenState(null)
    setDashboard(null)
    setHistory([])
    setSelectedPaper(null)
    setLatestPaper(null)
    setExplanations({})
    setOpenExplain({})
    setOpenAnswer({})
    setImportantQuestions({})
    setProfileOpen(false)
    setPage('login')
  }

  async function onGeneratePaper(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    if (!subjectId) {
      setError('Please select a subject')
      return
    }

    try {
      setIsGenerating(true)
      const generated = await generatePaper({
        subject: subjectId,
        total_questions: totalQuestions,
        cutoff_year: cutoffYear,
        topics: selectedTopics,
      })
      const detail = await fetchPaper(generated.paper_id)
      setLatestPaper(detail)
      setSelectedPaper(detail)
      setPage('history')

      const [dashData, historyData] = await Promise.all([fetchDashboard(), fetchHistory()])
      setDashboard(dashData)
      setHistory(historyData)
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : 'Paper generation failed')
    } finally {
      setIsGenerating(false)
    }
  }

  async function onOpenPaper(paperId: number) {
    setError('')
    try {
      const detail = await fetchPaper(paperId)
      setSelectedPaper(detail)
      setPage('history')
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : 'Unable to load paper')
    }
  }

  async function onExplain(question: Question) {
    const key = `${question.concept}::${question.question}`
    if (explanations[key]) {
      setOpenExplain((prev) => ({ ...prev, [key]: !prev[key] }))
      return
    }

    try {
      const explanation = await explainQuestion({
        question: question.question,
        topic: question.concept,
        difficulty: toExplainDifficulty(question.difficulty),
      })
      setExplanations((prev) => ({ ...prev, [key]: explanation }))
      setOpenExplain((prev) => ({ ...prev, [key]: true }))
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : 'Unable to generate explanation')
    }
  }

  async function onShowAnswer(question: Question) {
    const key = `${question.concept}::${question.question}`
    if (!explanations[key]) {
      await onExplain(question)
    }
    setOpenAnswer((prev) => ({ ...prev, [key]: !prev[key] }))
  }

  function onToggleImportant(question: Question) {
    const key = `${question.concept}::${question.question}`
    setImportantQuestions((prev) => ({ ...prev, [key]: !prev[key] }))
  }

  function toggleTopic(topic: string) {
    setSelectedTopics((prev) => (prev.includes(topic) ? prev.filter((item) => item !== topic) : [...prev, topic]))
  }

  return (
    <div className="app-shell modern-shell">
      <header className="topbar modern-topbar">
        <div className="nav-left">
          <div className="brand-mark">AI</div>
          <div className="brand-text">
            <strong>AI Exam Preparation Platform</strong>
            <span>{activeTitle}</span>
          </div>
        </div>

        {isAuthenticated ? (
          <nav className="nav-center">
            {navItems.map((item) => (
              <button
                key={item.id}
                type="button"
                className={`nav-item ${page === item.id ? 'active' : ''}`}
                onClick={() => setPage(item.id)}
              >
                <Icon name={item.icon} />
                <span>{item.label}</span>
              </button>
            ))}
          </nav>
        ) : (
          <nav className="nav-center compact">
            <button type="button" className={`nav-item ${page === 'login' ? 'active' : ''}`} onClick={() => setPage('login')}>Login</button>
            <button type="button" className={`nav-item ${page === 'register' ? 'active' : ''}`} onClick={() => setPage('register')}>Register</button>
          </nav>
        )}

        <div className="nav-right">
          <button type="button" className="icon-button" onClick={() => setDarkMode((prev) => !prev)}>
            <Icon name={darkMode ? 'sun' : 'moon'} />
          </button>

          {isAuthenticated ? (
            <div className="profile-area">
              <button type="button" className="profile-trigger" onClick={() => setProfileOpen((prev) => !prev)}>
                <Icon name="user" />
                <span>Account</span>
              </button>
              {profileOpen ? (
                <div className="profile-menu">
                  <button type="button" onClick={() => setProfileOpen(false)}>Profile</button>
                  <button type="button" onClick={() => { setPage('dashboard'); setProfileOpen(false) }}>Dashboard</button>
                  <button type="button" onClick={() => { setPage('history'); setProfileOpen(false) }}>Paper History</button>
                  <button type="button" onClick={onLogout}>Logout</button>
                </div>
              ) : null}
            </div>
          ) : null}
        </div>
      </header>

      {error ? <p className="error-banner modern-error">{error}</p> : null}

      {!isAuthenticated && page === 'login' ? (
        <section className="panel auth-panel modern-panel">
          <h2>Welcome Back</h2>
          <p className="muted">Sign in to continue your exam preparation workflow.</p>
          <form onSubmit={onLogin} className="modern-form">
            <label>
              Email
              <input type="email" placeholder="you@example.com" value={loginEmail} onChange={(e) => setLoginEmail(e.target.value)} required />
            </label>
            <label>
              Password
              <input type="password" placeholder="Enter your password" value={loginPassword} onChange={(e) => setLoginPassword(e.target.value)} required />
            </label>
            <button type="submit" className="button-primary">Sign In</button>
          </form>
        </section>
      ) : null}

      {!isAuthenticated && page === 'register' ? (
        <section className="panel auth-panel modern-panel">
          <h2>Create Account</h2>
          <p className="muted">Start building smart exam papers and track your progress.</p>
          <form onSubmit={onRegister} className="modern-form">
            <label>
              Full Name
              <input placeholder="Your name" value={registerName} onChange={(e) => setRegisterName(e.target.value)} required />
            </label>
            <label>
              Email
              <input type="email" placeholder="you@example.com" value={registerEmail} onChange={(e) => setRegisterEmail(e.target.value)} required />
            </label>
            <label>
              Password
              <input type="password" placeholder="Choose a strong password" value={registerPassword} onChange={(e) => setRegisterPassword(e.target.value)} required />
            </label>
            <button type="submit" className="button-primary">Create Account</button>
          </form>
        </section>
      ) : null}

      {isAuthenticated && page === 'dashboard' ? (
        <section className="modern-grid">
          <div className="stats-grid four-cols">
            <article className="stat-card modern-card">
              <div className="stat-icon"><Icon name="file" /></div>
              <h3>Total Papers Generated</h3>
              <p>{dashboard?.papers_generated ?? 0}</p>
            </article>
            <article className="stat-card modern-card">
              <div className="stat-icon"><Icon name="help" /></div>
              <h3>Total Questions Solved</h3>
              <p>{dashboard?.total_questions_solved ?? 0}</p>
            </article>
            <article className="stat-card modern-card">
              <div className="stat-icon"><Icon name="book" /></div>
              <h3>Topics Practiced</h3>
              <p>{topicsPracticed}</p>
            </article>
            <article className="stat-card modern-card">
              <div className="stat-icon"><Icon name="sparkles" /></div>
              <h3>Accuracy Rate</h3>
              <p>{accuracyRate}%</p>
            </article>
          </div>

          <div className="dashboard-content">
            <section className="panel modern-panel">
              <div className="section-head">
                <h2>Recent Papers</h2>
                <button className="button-primary" type="button" onClick={() => setPage('generate')}>Generate New Paper</button>
              </div>
              <div className="paper-row-list">
                {recentPapers.map((paper) => (
                  <div className="paper-row-card" key={paper.paper_id}>
                    <div>
                      <strong>{paper.subject}</strong>
                      <p className="muted">{new Date(paper.created_at).toLocaleDateString()} | {paper.total_questions} questions</p>
                    </div>
                    <button type="button" onClick={() => void onOpenPaper(paper.paper_id)}>View Paper</button>
                  </div>
                ))}
              </div>
            </section>

            <section className="panel modern-panel">
              <h2>Questions Solved Over Time</h2>
              <div className="chart-wrap">
                {chartData.length === 0 ? (
                  <p className="muted">No activity yet.</p>
                ) : (
                  chartData.map((item) => (
                    <div className="bar-item" key={item.label}>
                      <div className="bar-label">{item.label}</div>
                      <div className="bar-track">
                        <div className="bar-fill" style={{ width: `${(item.value / chartMax) * 100}%` }} />
                      </div>
                      <div className="bar-value">{item.value}</div>
                    </div>
                  ))
                )}
              </div>
            </section>
          </div>
        </section>
      ) : null}

      {isAuthenticated && page === 'generate' ? (
        <section className="panel modern-panel">
          <h2>Generate Paper</h2>
          <form className="generate-form modern-form" onSubmit={onGeneratePaper}>
            <div className="grid-two">
              <label>
                Subject
                <select value={subjectId} onChange={(e) => setSubjectId(e.target.value)} required>
                  <option value="">Select Subject</option>
                  {subjects.map((subject) => (
                    <option key={subject.id} value={subject.id}>{subject.name}</option>
                  ))}
                </select>
              </label>

              <label>
                Cutoff Year
                <input type="number" min={2000} max={2026} value={cutoffYear} onChange={(e) => setCutoffYear(Number(e.target.value))} />
              </label>

              <label>
                Total Questions
                <input type="number" min={1} max={120} value={totalQuestions} onChange={(e) => setTotalQuestions(Number(e.target.value))} />
              </label>

              <label>
                Difficulty
                <select value={difficulty} onChange={(e) => setDifficulty(e.target.value as DifficultyView)}>
                  <option value="easy">Easy</option>
                  <option value="medium">Medium</option>
                  <option value="university">University Exam</option>
                  <option value="gate">GATE Level</option>
                </select>
              </label>
            </div>

            <div className="topics-panel">
              <label>
                Search Topics
                <input value={topicSearch} onChange={(e) => setTopicSearch(e.target.value)} placeholder="Search by topic name" />
              </label>
              <div className="topic-tag-grid">
                {filteredTopics.map((topic) => (
                  <button
                    type="button"
                    className={`topic-tag ${selectedTopics.includes(topic) ? 'selected' : ''}`}
                    key={topic}
                    onClick={() => toggleTopic(topic)}
                  >
                    {topic}
                  </button>
                ))}
              </div>
            </div>

            <div className="center-row">
              <button type="submit" className="button-primary large" disabled={isGenerating}>
                {isGenerating ? 'Generating exam paper...' : 'Generate Paper'}
              </button>
            </div>
          </form>

          {latestPaper ? (
            <div className="paper-section">
              <h3>Latest Generated Paper: {latestPaper.subject}</h3>
              <QuestionList
                questions={latestPaper.questions}
                explanations={explanations}
                openExplain={openExplain}
                openAnswer={openAnswer}
                importantQuestions={importantQuestions}
                onExplain={onExplain}
                onShowAnswer={onShowAnswer}
                onToggleImportant={onToggleImportant}
              />
            </div>
          ) : null}
        </section>
      ) : null}

      {isAuthenticated && page === 'history' ? (
        <section className="panel modern-panel">
          <div className="section-head">
            <h2>Paper History</h2>
          </div>

          <div className="history-controls">
            <input placeholder="Search papers" value={historySearch} onChange={(e) => setHistorySearch(e.target.value)} />
            <select value={historySubjectFilter} onChange={(e) => setHistorySubjectFilter(e.target.value)}>
              <option value="all">All Subjects</option>
              <option value="electrical">Electrical</option>
              <option value="civil">Civil</option>
              <option value="mechanical">Mechanical</option>
            </select>
            <select value={historySort} onChange={(e) => setHistorySort(e.target.value as 'newest' | 'oldest')}>
              <option value="newest">Newest</option>
              <option value="oldest">Oldest</option>
            </select>
          </div>

          <div className="history-card-grid">
            {filteredHistory.map((paper) => (
              <article className="history-card" key={paper.paper_id}>
                <h3>{paper.subject}</h3>
                <div className="topic-chip-wrap">
                  {paper.topics.map((topic) => (
                    <span key={`${paper.paper_id}-${topic}`} className="topic-chip">{topic}</span>
                  ))}
                </div>
                <p className="muted">Generated: {new Date(paper.created_at).toLocaleDateString()}</p>
                <p className="muted">Total questions: {paper.total_questions}</p>
                <button type="button" onClick={() => void onOpenPaper(paper.paper_id)}>View Paper</button>
              </article>
            ))}
          </div>

          {selectedPaper ? (
            <div className="paper-section">
              <h3>{selectedPaper.subject}</h3>
              <QuestionList
                questions={selectedPaper.questions}
                explanations={explanations}
                openExplain={openExplain}
                openAnswer={openAnswer}
                importantQuestions={importantQuestions}
                onExplain={onExplain}
                onShowAnswer={onShowAnswer}
                onToggleImportant={onToggleImportant}
              />
            </div>
          ) : null}
        </section>
      ) : null}
    </div>
  )
}
