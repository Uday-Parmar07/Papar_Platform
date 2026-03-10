import { useEffect, useMemo, useState } from 'react'
import { downloadPdf, fetchSubjects, fetchTopics, generateExam } from './services/api'
import { BranchSelector, type Branch } from './components/BranchSelector'
import { ExamSettings } from './components/ExamSettings'
import { LandingPage } from './components/LandingPage'
import { LoadingScreen } from './components/LoadingScreen'
import { Navbar } from './components/Navbar'
import { PaperPreview } from './components/PaperPreview'
import { PredictedPaper } from './components/PredictedPaper'
import { Stepper } from './components/Stepper'
import { SubjectSelector } from './components/SubjectSelector'
import { TopicSelector, type TopicItem } from './components/TopicSelector'
import { YearRangeSlider } from './components/YearRangeSlider'
import type { Question, SubjectOption } from './types'

type Screen = 'landing' | 'wizard' | 'loading' | 'result'

const stepNames = ['Branch', 'Subject', 'Topics', 'Year Range', 'Generate']

const branches: Branch[] = [
  {
    id: 'ee',
    name: 'Electrical Engineering',
    description: 'Machines, power systems, control systems, and power electronics.',
  },
  {
    id: 'cs',
    name: 'Computer Science',
    description: 'Data structures, operating systems, DBMS, and machine learning.',
  },
  {
    id: 'me',
    name: 'Mechanical Engineering',
    description: 'Thermodynamics, manufacturing, fluid mechanics, and design.',
  },
  {
    id: 'ce',
    name: 'Civil Engineering',
    description: 'Structural analysis, RCC, geotechnical and transportation topics.',
  },
  {
    id: 'ec',
    name: 'Electronics',
    description: 'Signals, communication systems, VLSI and analog electronics.',
  },
]

const branchKeywords: Record<string, string[]> = {
  ee: ['electrical', 'power', 'machine'],
  cs: ['computer', 'cs', 'software', 'algorithm'],
  me: ['mechanical', 'thermo', 'manufacturing'],
  ce: ['civil', 'structural', 'construction', 'transportation'],
  ec: ['electronics', 'communication', 'signal', 'vlsi'],
}

function mapTopicsWithHints(topics: string[]): TopicItem[] {
  return topics.map((name, index) => ({
    name,
    frequent: index % 2 === 0,
    highWeightage: index % 3 === 0,
  }))
}

function normalizeTopicName(value: string): string {
  return value.trim().replace(/\s+/g, ' ')
}

function dedupeTopics(values: string[]): string[] {
  const seen = new Set<string>()
  const result: string[] = []
  values.forEach((raw) => {
    const topic = normalizeTopicName(raw)
    if (!topic) return
    const key = topic.toLowerCase()
    if (seen.has(key)) return
    seen.add(key)
    result.push(topic)
  })
  return result
}

function estimateTopicAvailability(topic: string, fromYear: number, toYear: number, custom: boolean): number {
  let hash = 0
  for (const char of topic.toLowerCase()) {
    hash = (hash * 31 + char.charCodeAt(0)) % 997
  }
  const spanBoost = Math.max(1, Math.floor((toYear - fromYear + 1) / 4))
  const base = custom ? 1 : 3
  return Math.max(1, Math.min(12, base + spanBoost + (hash % 6)))
}

function App() {
  const [screen, setScreen] = useState<Screen>('landing')
  const [currentStep, setCurrentStep] = useState(0)
  const [branchId, setBranchId] = useState<string | null>(null)
  const [subjectSearch, setSubjectSearch] = useState('')
  const [subjectId, setSubjectId] = useState<string | null>(null)
  const [subjectName, setSubjectName] = useState<string | null>(null)
  const [subjects, setSubjects] = useState<SubjectOption[]>([])
  const [topics, setTopics] = useState<string[]>([])
  const [selectedTopics, setSelectedTopics] = useState<string[]>([])
  const [customTopics, setCustomTopics] = useState<string[]>([])
  const [customTopicInput, setCustomTopicInput] = useState('')
  const [generatedQuestions, setGeneratedQuestions] = useState<Question[]>([])
  const [fetchingSubjects, setFetchingSubjects] = useState(false)
  const [fetchingTopics, setFetchingTopics] = useState(false)
  const [fromYear, setFromYear] = useState(2012)
  const [toYear, setToYear] = useState(2024)
  const [duration, setDuration] = useState(3)
  const [totalMarks, setTotalMarks] = useState(70)
  const [difficulty, setDifficulty] = useState(1)
  const [totalQuestions, setTotalQuestions] = useState(15)
  const [useSectionDistribution, setUseSectionDistribution] = useState(false)
  const [sectionAShort, setSectionAShort] = useState(5)
  const [sectionBMedium, setSectionBMedium] = useState(6)
  const [sectionCLong, setSectionCLong] = useState(4)
  const [autoBalanceTopics, setAutoBalanceTopics] = useState(true)
  const [generateAdvisory, setGenerateAdvisory] = useState<{ issues: string[]; directAvailable: number } | null>(null)
  const [loadingMessage, setLoadingMessage] = useState('Analyzing previous papers...')
  const [paperGeneratedAt, setPaperGeneratedAt] = useState<string>('')
  const [error, setError] = useState<string | null>(null)

  const selectedBranch = branches.find((branch) => branch.id === branchId)
  const availableTopics = useMemo(() => mapTopicsWithHints(topics), [topics])
  const mergedTopics = useMemo(() => dedupeTopics([...selectedTopics, ...customTopics]), [selectedTopics, customTopics])

  const topicAvailability = useMemo(() => {
    const values: Record<string, number> = {}
    availableTopics.forEach((topic) => {
      values[topic.name] = estimateTopicAvailability(topic.name, fromYear, toYear, false)
    })
    customTopics.forEach((topic) => {
      values[topic] = estimateTopicAvailability(topic, fromYear, toYear, true)
    })
    return values
  }, [availableTopics, customTopics, fromYear, toYear])

  const lowCoverageTopics = useMemo(
    () => mergedTopics.filter((topic) => (topicAvailability[topic] ?? 0) <= 3),
    [mergedTopics, topicAvailability],
  )

  const estimatedDirectAvailability = useMemo(() => {
    const sum = mergedTopics.reduce((acc, topic) => acc + (topicAvailability[topic] ?? 0), 0)
    return Math.round(sum * 0.45)
  }, [mergedTopics, topicAvailability])

  const fallbackNotice =
    mergedTopics.length > 0 && estimatedDirectAvailability < totalQuestions
      ? `Not enough questions found for the selected topics and years. The generator will include related topics to reach the requested question count.`
      : null

  const sectionTotal = sectionAShort + sectionBMedium + sectionCLong
  const sectionSumMismatch = useSectionDistribution && sectionTotal !== totalQuestions

  const branchFilteredSubjects = useMemo(() => {
    if (!branchId) return subjects
    const hints = branchKeywords[branchId] ?? []
    const matches = subjects.filter((item) => {
      const value = `${item.name} ${item.id}`.toLowerCase()
      return hints.some((hint) => value.includes(hint))
    })
    return matches.length > 0 ? matches : subjects
  }, [branchId, subjects])

  const filteredSubjects = useMemo(() => {
    const query = subjectSearch.toLowerCase().trim()
    if (!query) return branchFilteredSubjects
    return branchFilteredSubjects.filter((item) => item.name.toLowerCase().includes(query))
  }, [branchFilteredSubjects, subjectSearch])

  useEffect(() => {
    let active = true

    async function loadSubjects() {
      setFetchingSubjects(true)
      setError(null)
      try {
        const response = await fetchSubjects()
        if (!active) return
        setSubjects(response.subjects)
      } catch (err) {
        if (!active) return
        setError(err instanceof Error ? err.message : 'Unable to load subjects')
      } finally {
        if (active) setFetchingSubjects(false)
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

      setFetchingTopics(true)
      setError(null)
      try {
        const response = await fetchTopics(subjectId)
        if (!active) return
        setTopics(response.topics)
        setSelectedTopics(response.topics.slice(0, 6))
        setCustomTopics([])
        setCustomTopicInput('')
      } catch (err) {
        if (!active) return
        setError(err instanceof Error ? err.message : 'Unable to load topics')
      } finally {
        if (active) setFetchingTopics(false)
      }
    }

    loadTopics()
    return () => {
      active = false
    }
  }, [subjectId])

  useEffect(() => {
    if (!subjectId) {
      setSubjectName(null)
      setSelectedTopics([])
      return
    }

    const selected = subjects.find((item) => item.id === subjectId)
    setSubjectName(selected?.name ?? subjectId)
  }, [subjectId, subjects])

  const difficultyLabel = ['Easy', 'Medium', 'Hard'][difficulty]

  const previewData = {
    branch: selectedBranch?.name ?? '',
    subject: subjectName ?? '',
    topics: mergedTopics,
    fromYear,
    toYear,
    duration,
    totalMarks,
    difficulty: difficultyLabel,
  }

  const generatedPaper = useMemo(() => {
    const easyQuestions = generatedQuestions
      .filter((question) => question.difficulty.toLowerCase().includes('easy'))
      .map((question) => question.question)
    const hardQuestions = generatedQuestions
      .filter((question) => question.difficulty.toLowerCase().includes('hard'))
      .map((question) => question.question)
    const mediumQuestions = generatedQuestions
      .filter((question) => !question.difficulty.toLowerCase().includes('easy') && !question.difficulty.toLowerCase().includes('hard'))
      .map((question) => question.question)

    const shortQuestions = easyQuestions.length > 0 ? easyQuestions : mediumQuestions.slice(0, 5)
    const numericalQuestions = mediumQuestions.length > 0 ? mediumQuestions : easyQuestions.slice(0, 3)
    const longQuestions = hardQuestions.length > 0 ? hardQuestions : mediumQuestions.slice(0, 3)

    const finalShort = useSectionDistribution ? shortQuestions.slice(0, sectionAShort) : shortQuestions
    const finalNumerical = useSectionDistribution ? numericalQuestions.slice(0, sectionBMedium) : numericalQuestions
    const finalLong = useSectionDistribution ? longQuestions.slice(0, sectionCLong) : longQuestions

    return {
      subject: subjectName ?? 'Selected Subject',
      duration,
      totalMarks,
      shortQuestions: finalShort,
      numericalQuestions: finalNumerical,
      longQuestions: finalLong,
    }
  }, [
    duration,
    generatedQuestions,
    sectionAShort,
    sectionBMedium,
    sectionCLong,
    subjectName,
    totalMarks,
    useSectionDistribution,
  ])

  const goToNextStep = () => setCurrentStep((step) => Math.min(step + 1, stepNames.length - 1))
  const goToPreviousStep = () => setCurrentStep((step) => Math.max(step - 1, 0))

  const handleStart = () => setScreen('wizard')

  const buildGenerateTopics = () => {
    const chosen = [...mergedTopics]
    if (!autoBalanceTopics || estimatedDirectAvailability >= totalQuestions) return chosen

    const selectedSet = new Set(chosen.map((topic) => topic.toLowerCase()))
    const relatedCandidates = availableTopics
      .filter((topic) => !selectedSet.has(topic.name.toLowerCase()))
      .sort((a, b) => {
        const scoreA = Number(Boolean(a.highWeightage)) * 2 + Number(Boolean(a.frequent))
        const scoreB = Number(Boolean(b.highWeightage)) * 2 + Number(Boolean(b.frequent))
        return scoreB - scoreA
      })
      .map((topic) => topic.name)

    for (const topic of relatedCandidates) {
      if (chosen.length >= mergedTopics.length + 6) break
      chosen.push(topic)
      const projected = Math.round(chosen.reduce((acc, name) => acc + (topicAvailability[name] ?? 2), 0) * 0.45)
      if (projected >= totalQuestions) break
    }

    return dedupeTopics(chosen)
  }

  const buildGenerationIssues = () => {
    const issues: string[] = []
    if (totalQuestions < 4 || totalQuestions > 40) {
      issues.push('Total questions should be between 4 and 40.')
    }
    if (sectionSumMismatch) {
      issues.push('Section distribution does not match the total question count.')
    }
    if (estimatedDirectAvailability < totalQuestions) {
      issues.push(
        `You requested ${totalQuestions} questions but only ${estimatedDirectAvailability} are directly available from selected topics.`,
      )
    }
    if (lowCoverageTopics.length > 0) {
      issues.push(`Limited historical coverage for: ${lowCoverageTopics.join(', ')}.`)
    }
    return issues
  }

  const runGenerate = async () => {
    if (!subjectId) {
      setError('Please select a subject before generating the paper.')
      return
    }
    if (mergedTopics.length === 0) {
      setError('Please select at least one topic before generating the paper.')
      return
    }

    const issues = buildGenerationIssues()
    if (issues.length > 0) {
      setGenerateAdvisory({ issues, directAvailable: estimatedDirectAvailability })
      return
    }

    await performGenerate()
  }

  const performGenerate = async () => {
    if (!subjectId) {
      setError('Please select a subject before generating the paper.')
      return
    }

    const generateTopics = buildGenerateTopics()

    setError(null)
    setGenerateAdvisory(null)
    setScreen('loading')
    setLoadingMessage('Analyzing previous papers...')

    const messages = [
      'Analyzing previous papers...',
      'Detecting topic patterns...',
      'Generating predicted questions...',
    ]

    let index = 0
    const interval = window.setInterval(() => {
      index += 1
      if (index < messages.length) setLoadingMessage(messages[index])
    }, 1200)

    try {
      const response = await generateExam({
        subject: subjectId,
        total_questions: totalQuestions,
        cutoff_year: toYear,
        topics: generateTopics,
      })

      setGeneratedQuestions(response.questions)
      setSubjectName(response.subject_name)
      window.clearInterval(interval)
      setPaperGeneratedAt(new Date().toLocaleString())
      setScreen('result')
    } catch (err) {
      window.clearInterval(interval)
      setScreen('wizard')
      setCurrentStep(4)
      setError(err instanceof Error ? err.message : 'Unable to generate predicted paper')
    }
  }

  const addCustomTopic = () => {
    const next = normalizeTopicName(customTopicInput)
    if (!next) return
    setCustomTopics((current) => dedupeTopics([...current, next]))
    setCustomTopicInput('')
  }

  const handleDownload = async () => {
    if (generatedQuestions.length === 0) return

    try {
      const blob = await downloadPdf({
        questions: generatedQuestions,
        title: `Predicted Examination Paper - ${subjectName ?? 'Subject'}`,
      })
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = 'predicted-exam-paper.pdf'
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(url)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to download PDF')
    }
  }

  const canContinue =
    (currentStep === 0 && branchId) ||
    (currentStep === 1 && subjectId) ||
    (currentStep === 2 && mergedTopics.length > 0) ||
    currentStep >= 3

  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 via-white to-indigo-50 text-slate-900">
      <Navbar onStart={handleStart} />

      {screen === 'landing' && (
        <>
          <LandingPage onStart={handleStart} />
          <section id="about" className="mx-auto w-full max-w-7xl px-4 pb-8 text-sm text-slate-600 sm:px-6 lg:px-8">
            Built for engineering students to convert historical exam trends into practical revision strategy.
          </section>
          <section id="help" className="mx-auto w-full max-w-7xl px-4 pb-12 text-sm text-slate-600 sm:px-6 lg:px-8">
            Select your branch, subject, topics and year range. Then tune the exam settings and generate a predicted
            paper.
          </section>
        </>
      )}

      {screen === 'wizard' && (
        <main className="mx-auto grid w-full max-w-7xl gap-6 px-4 pb-10 pt-6 sm:px-6 lg:grid-cols-[minmax(0,1fr)_420px] lg:px-8">
          <section className="animate-fade-in-up rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-7">
            <Stepper steps={stepNames} currentStep={currentStep} />

            {error && (
              <div className="mt-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>
            )}

            <div className="mt-6 min-h-[calc(100vh-14rem)] sm:min-h-[480px]">
              {currentStep === 0 && (
                <div className="grid gap-4">
                  <h2 className="text-xl font-semibold text-slate-900">Select Engineering Branch</h2>
                  <BranchSelector
                    branches={branches}
                    selectedBranch={branchId}
                    onSelect={(id) => {
                      setBranchId(id)
                      setSubjectId(null)
                      setSubjectName(null)
                      setTopics([])
                      setGeneratedQuestions([])
                      setSubjectSearch('')
                      setTimeout(goToNextStep, 120)
                    }}
                  />
                </div>
              )}

              {currentStep === 1 && (
                <div className="grid gap-4">
                  <h2 className="text-xl font-semibold text-slate-900">Select Subject</h2>
                  {fetchingSubjects && <p className="text-sm text-slate-500">Loading subjects...</p>}
                  <SubjectSelector
                    subjects={filteredSubjects.map((item) => item.name)}
                    selectedSubject={subjectName}
                    search={subjectSearch}
                    onSearch={setSubjectSearch}
                    onSelect={(nextSubject) => {
                      const match = filteredSubjects.find((item) => item.name === nextSubject)
                      if (!match) return
                      setSubjectId(match.id)
                      setSubjectName(match.name)
                      setGeneratedQuestions([])
                      setTimeout(goToNextStep, 120)
                    }}
                  />
                </div>
              )}

              {currentStep === 2 && (
                <div className="grid gap-4">
                  <h2 className="text-xl font-semibold text-slate-900">Select Topics</h2>
                  {fetchingTopics && <p className="text-sm text-slate-500">Loading topics...</p>}
                  <TopicSelector
                    topics={availableTopics}
                    selectedTopics={selectedTopics}
                    customTopics={customTopics}
                    customTopicInput={customTopicInput}
                    topicAvailability={topicAvailability}
                    lowCoverageTopics={lowCoverageTopics}
                    fallbackNotice={fallbackNotice}
                    onToggleTopic={(topicName) => {
                      setSelectedTopics((current) =>
                        current.includes(topicName)
                          ? current.filter((item) => item !== topicName)
                          : [...current, topicName],
                      )
                    }}
                    onSelectAll={() => setSelectedTopics(availableTopics.map((topic) => topic.name))}
                    onClear={() => setSelectedTopics([])}
                    onCustomTopicInputChange={setCustomTopicInput}
                    onAddCustomTopic={addCustomTopic}
                    onRemoveCustomTopic={(topicName) =>
                      setCustomTopics((current) => current.filter((topic) => topic.toLowerCase() !== topicName.toLowerCase()))
                    }
                  />
                </div>
              )}

              {currentStep === 3 && (
                <div className="grid gap-4">
                  <h2 className="text-xl font-semibold text-slate-900">Previous Year Range</h2>
                  <p className="text-sm text-slate-600">Choose the span of papers used for prediction analytics.</p>
                  <YearRangeSlider
                    minYear={2008}
                    maxYear={2024}
                    fromYear={fromYear}
                    toYear={toYear}
                    onFromChange={setFromYear}
                    onToChange={setToYear}
                  />
                </div>
              )}

              {currentStep === 4 && (
                <div className="grid gap-4">
                  <h2 className="text-xl font-semibold text-slate-900">Exam Settings</h2>
                  <ExamSettings
                    duration={duration}
                    totalMarks={totalMarks}
                    difficulty={difficulty}
                    totalQuestions={totalQuestions}
                    useSectionDistribution={useSectionDistribution}
                    sectionAShort={sectionAShort}
                    sectionBMedium={sectionBMedium}
                    sectionCLong={sectionCLong}
                    sectionSumMismatch={sectionSumMismatch}
                    autoBalanceTopics={autoBalanceTopics}
                    onDurationChange={setDuration}
                    onMarksChange={setTotalMarks}
                    onDifficultyChange={setDifficulty}
                    onTotalQuestionsChange={(value) => setTotalQuestions(Math.max(4, Math.min(40, Number.isFinite(value) ? value : 4)))}
                    onUseSectionDistributionChange={setUseSectionDistribution}
                    onSectionAShortChange={(value) => setSectionAShort(Math.max(0, Math.min(40, Number.isFinite(value) ? value : 0)))}
                    onSectionBMediumChange={(value) => setSectionBMedium(Math.max(0, Math.min(40, Number.isFinite(value) ? value : 0)))}
                    onSectionCLongChange={(value) => setSectionCLong(Math.max(0, Math.min(40, Number.isFinite(value) ? value : 0)))}
                    onAutoBalanceTopicsChange={setAutoBalanceTopics}
                  />

                  {generateAdvisory && (
                    <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
                      <p className="font-semibold">
                        You requested {totalQuestions} questions but only {generateAdvisory.directAvailable} are directly available from selected topics.
                      </p>
                      <ul className="mt-2 list-disc pl-5 text-xs">
                        {generateAdvisory.issues.map((issue) => (
                          <li key={issue}>{issue}</li>
                        ))}
                      </ul>
                      <div className="mt-3 flex flex-wrap gap-2">
                        <button
                          type="button"
                          onClick={() => setGenerateAdvisory(null)}
                          className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 transition hover:bg-slate-50"
                        >
                          Adjust Settings
                        </button>
                        <button
                          type="button"
                          onClick={performGenerate}
                          className="rounded-lg bg-brand-600 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-brand-700"
                        >
                          Continue Anyway
                        </button>
                      </div>
                    </div>
                  )}

                  <button
                    onClick={runGenerate}
                    className="mt-2 rounded-2xl bg-brand-600 px-6 py-4 text-base font-semibold text-white shadow-lg shadow-blue-100 transition hover:bg-brand-700"
                  >
                    Generate Predicted Paper
                  </button>
                </div>
              )}
            </div>

            <div className="mt-6 flex items-center justify-between gap-3">
              <button
                type="button"
                onClick={goToPreviousStep}
                disabled={currentStep === 0}
                className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-semibold text-slate-600 transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Back
              </button>

              {currentStep < 4 && (
                <button
                  type="button"
                  onClick={goToNextStep}
                  disabled={!canContinue}
                  className="rounded-xl bg-brand-600 px-5 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Continue
                </button>
              )}
            </div>
          </section>

          <div className="hidden lg:block">
            <PaperPreview data={previewData} generatedQuestions={generatedQuestions} />
          </div>
        </main>
      )}

      {screen === 'loading' && <LoadingScreen message={loadingMessage} />}

      {screen === 'result' && (
        <>
          <PredictedPaper
            paper={generatedPaper}
            onDownload={handleDownload}
            onRegenerate={runGenerate}
            onModifyTopics={() => {
              setScreen('wizard')
              setCurrentStep(2)
            }}
          />
          <p className="pb-10 text-center text-xs text-slate-500">Generated at: {paperGeneratedAt}</p>
        </>
      )}
    </div>
  )
}

export default App
