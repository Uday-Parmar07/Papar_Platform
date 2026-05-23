import { useEffect, useState, useCallback } from 'react'
import Sidebar from '../components/Sidebar'
import GeneratorForm from '../components/GeneratorForm'
import PreviewPanel from '../components/PreviewPanel'
import FeatureCards from '../components/FeatureCards'
import { Menu, FileText } from '../components/icons'
import { fetchSubjects, fetchTopics, generatePaper } from '../services/api'
import type { GeneratePaperQuestion } from '../types'

interface HistoryItem {
  id: string
  subject: string
  questionCount: number
  timestamp: string
  isActive?: boolean
  questions: GeneratePaperQuestion[]
}

export default function Dashboard() {
  // State
  const [subjects, setSubjects] = useState<string[]>([])
  const [topics, setTopics] = useState<string[]>([])
  const [selectedSubject, setSelectedSubject] = useState('')
  const [selectedTopics, setSelectedTopics] = useState<string[]>([])
  const [startYear, setStartYear] = useState(2015)
  const [endYear, setEndYear] = useState(2025)
  const [questionCount, setQuestionCount] = useState(25)
  const [generatedQuestions, setGeneratedQuestions] = useState<GeneratePaperQuestion[]>([])
  const [loading, setLoading] = useState(false)
  const [subjectsLoading, setSubjectsLoading] = useState(false)
  const [topicsLoading, setTopicsLoading] = useState(false)
  const [error, setError] = useState('')
  const [history, setHistory] = useState<HistoryItem[]>([])
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  // Load subjects on mount
  useEffect(() => {
    async function loadSubjects() {
      setSubjectsLoading(true)
      try {
        const data = await fetchSubjects()
        setSubjects(data.subjects)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unable to load subjects')
      } finally {
        setSubjectsLoading(false)
      }
    }
    void loadSubjects()
  }, [])

  // Load topics when subject changes
  useEffect(() => {
    async function loadTopics() {
      if (!selectedSubject) {
        setTopics([])
        setSelectedTopics([])
        return
      }
      setTopicsLoading(true)
      try {
        const data = await fetchTopics(selectedSubject)
        setTopics(data.topics)
        setSelectedTopics([])
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unable to load topics')
      } finally {
        setTopicsLoading(false)
      }
    }
    void loadTopics()
  }, [selectedSubject])

  // Handle subject selection
  const handleSelectSubject = useCallback((subject: string) => {
    setSelectedSubject(subject)
    setError('')
  }, [])

  // Handle topic toggle
  const handleTopicToggle = useCallback((topic: string) => {
    setSelectedTopics((prev) =>
      prev.includes(topic) ? prev.filter((t) => t !== topic) : [...prev, topic]
    )
  }, [])

  // Handle year range change
  const handleYearRangeChange = useCallback((start: number, end: number) => {
    setStartYear(start)
    setEndYear(end)
  }, [])

  // Handle question count change
  const handleQuestionCountChange = useCallback((count: number) => {
    setQuestionCount(count)
  }, [])

  // Handle generate paper
  const handleGenerate = useCallback(async () => {
    if (!selectedSubject || selectedTopics.length === 0) {
      setError('Please select a subject and at least one topic')
      return
    }

    setError('')
    setLoading(true)

    try {
      const response = await generatePaper({
        subject: selectedSubject,
        topics: selectedTopics,
        cutoff_year: endYear,
        num_questions: questionCount,
      })

      setGeneratedQuestions(response.questions)

      // Add to history
      const newHistoryItem: HistoryItem = {
        id: Date.now().toString(),
        subject: selectedSubject,
        questionCount: response.questions.length,
        timestamp: 'Just now',
        isActive: true,
        questions: response.questions,
      }

      setHistory((prev) =>
        [newHistoryItem, ...prev.map((item) => ({ ...item, isActive: false }))].slice(0, 10)
      )
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Paper generation failed')
    } finally {
      setLoading(false)
    }
  }, [selectedSubject, selectedTopics, endYear, questionCount])

  // Handle history selection
  const handleSelectHistory = useCallback((id: string) => {
    const item = history.find((h) => h.id === id)
    if (item) {
      setSelectedSubject(item.subject)
      setGeneratedQuestions(item.questions)
      setHistory((prev) =>
        prev.map((h) => ({ ...h, isActive: h.id === id }))
      )
    }
  }, [history])

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Mobile Header */}
      <header className="lg:hidden sticky top-0 z-50 bg-white border-b border-gray-200 px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
              <FileText className="w-5 h-5 text-white" />
            </div>
            <span className="font-bold text-gray-900">PaperGen</span>
          </div>
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <Menu className="w-6 h-6 text-gray-600" />
          </button>
        </div>
      </header>

      {/* Mobile Menu Overlay */}
      {mobileMenuOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={() => setMobileMenuOpen(false)}
        />
      )}

      {/* Layout */}
      <div className="flex">
        {/* Left Sidebar */}
        <div
          className={`fixed lg:static inset-y-0 left-0 z-50 transform transition-transform duration-300 lg:transform-none ${
            mobileMenuOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
          }`}
        >
          <Sidebar history={history} onSelectHistory={handleSelectHistory} />
        </div>

        {/* Main Content */}
        <main className="flex-1 min-w-0">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            {/* Error Banner */}
            {error && (
              <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">
                {error}
              </div>
            )}

            {/* Generator Form */}
            <GeneratorForm
              subjects={subjects}
              topics={topics}
              selectedSubject={selectedSubject}
              selectedTopics={selectedTopics}
              startYear={startYear}
              endYear={endYear}
              questionCount={questionCount}
              loading={loading}
              subjectsLoading={subjectsLoading}
              topicsLoading={topicsLoading}
              onSelectSubject={handleSelectSubject}
              onTopicToggle={handleTopicToggle}
              onYearRangeChange={handleYearRangeChange}
              onQuestionCountChange={handleQuestionCountChange}
              onGenerate={handleGenerate}
            />

            {/* Feature Cards */}
            <FeatureCards />
          </div>
        </main>

        {/* Right Sidebar - Preview Panel */}
        <PreviewPanel
          questions={generatedQuestions}
          subject={selectedSubject}
          loading={loading}
        />
      </div>
    </div>
  )
}
