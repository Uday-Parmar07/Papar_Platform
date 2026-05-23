import SubjectInput from './SubjectInput'
import TopicSelector from './TopicSelector'
import YearRangeSlider from './YearRangeSlider'
import QuestionCountSelector from './QuestionCountSelector'
import GenerateButton from './GenerateButton'

interface GeneratorFormProps {
  subjects: string[]
  topics: string[]
  selectedSubject: string
  selectedTopics: string[]
  startYear: number
  endYear: number
  questionCount: number
  loading: boolean
  subjectsLoading?: boolean
  topicsLoading?: boolean
  onSelectSubject: (subject: string) => void
  onTopicToggle: (topic: string) => void
  onYearRangeChange: (start: number, end: number) => void
  onQuestionCountChange: (count: number) => void
  onGenerate: () => void
}

export default function GeneratorForm({
  subjects,
  topics,
  selectedSubject,
  selectedTopics,
  startYear,
  endYear,
  questionCount,
  loading,
  subjectsLoading = false,
  topicsLoading = false,
  onSelectSubject,
  onTopicToggle,
  onYearRangeChange,
  onQuestionCountChange,
  onGenerate,
}: GeneratorFormProps) {
  const isValid = selectedSubject && selectedTopics.length > 0

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
      {/* Header */}
      <div className="px-8 pt-8 pb-6 border-b border-gray-100">
        <h2 className="text-2xl font-bold text-gray-900">
          Generate Your Question Paper
        </h2>
        <p className="text-gray-500 mt-2">
          Select your preferences to create a customized exam paper powered by AI
        </p>
      </div>

      {/* Form Content */}
      <div className="p-8 space-y-8">
        {/* Subject Input */}
        <SubjectInput
          subjects={subjects}
          selectedSubject={selectedSubject}
          onSelectSubject={onSelectSubject}
          loading={subjectsLoading}
        />

        {/* Topic Selector */}
        <TopicSelector
          availableTopics={topics}
          selectedTopics={selectedTopics}
          onTopicToggle={onTopicToggle}
          loading={topicsLoading}
          disabled={!selectedSubject}
        />

        {/* Year Range Slider */}
        <YearRangeSlider
          minYear={1990}
          maxYear={2025}
          startYear={startYear}
          endYear={endYear}
          onRangeChange={onYearRangeChange}
        />

        {/* Question Count Selector */}
        <QuestionCountSelector
          count={questionCount}
          min={5}
          max={100}
          onChange={onQuestionCountChange}
        />

        {/* Divider */}
        <div className="border-t border-gray-100 pt-6">
          {/* Generate Button */}
          <GenerateButton
            onClick={onGenerate}
            loading={loading}
            disabled={!isValid}
          />

          {/* Validation Message */}
          {!isValid && (
            <p className="text-center text-sm text-amber-600 mt-4">
              {!selectedSubject
                ? 'Please select a subject to continue'
                : 'Please select at least one topic'}
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
