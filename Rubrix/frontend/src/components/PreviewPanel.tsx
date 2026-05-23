import type { GeneratePaperQuestion } from '../types'
import { Eye, FileText, Maximize2, Minimize2, Code } from './icons'
import LatexPreview from './LatexPreview'

interface PreviewPanelProps {
  questions: GeneratePaperQuestion[]
  subject: string
  loading?: boolean
  expanded?: boolean
  onToggleExpand?: () => void
  latexView?: boolean
  onToggleLatexView?: () => void
}

interface QuestionSection {
  title: string
  marks: string
  questions: GeneratePaperQuestion[]
}

export default function PreviewPanel({
  questions,
  subject,
  loading = false,
  expanded = false,
  onToggleExpand,
  latexView = false,
  onToggleLatexView,
}: PreviewPanelProps) {
  // Group questions into sections (for demo purposes)
  const sections: QuestionSection[] = questions.length > 0
    ? [
        {
          title: 'Section A',
          marks: '2 marks each',
          questions: questions.slice(0, Math.ceil(questions.length * 0.4)),
        },
        {
          title: 'Section B',
          marks: '5 marks each',
          questions: questions.slice(Math.ceil(questions.length * 0.4)),
        },
      ]
    : []

  return (
    <aside className={`hidden lg:block h-screen sticky top-0 overflow-y-auto bg-white border-l border-gray-200 transition-all duration-300 ${expanded ? 'w-full' : 'w-[600px]'}`}>
      {/* Header */}
      <div className="p-6 border-b border-gray-100 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center">
            <Eye className="w-5 h-5 text-white" />
          </div>
          <div>
            <h2 className="font-bold text-gray-900 text-lg">Live Preview</h2>
            <p className="text-xs text-gray-500">Real-time paper preview</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {onToggleLatexView && (
            <button
              onClick={onToggleLatexView}
              className={`p-2 rounded-lg transition-colors ${latexView ? 'bg-indigo-100 text-indigo-600' : 'hover:bg-gray-100 text-gray-600'}`}
              title={latexView ? "Switch to normal view" : "Switch to LaTeX view"}
            >
              <Code className="w-5 h-5" />
            </button>
          )}
          {onToggleExpand && (
            <button
              onClick={onToggleExpand}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              title={expanded ? "Collapse preview" : "Expand preview"}
            >
              {expanded ? (
                <Minimize2 className="w-5 h-5 text-gray-600" />
              ) : (
                <Maximize2 className="w-5 h-5 text-gray-600" />
              )}
            </button>
          )}
        </div>
      </div>

      {/* Content */}
      {latexView ? (
        <LatexPreview questions={questions} subject={subject} />
      ) : (
        <div className="p-6">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-16">
              <div className="w-12 h-12 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin" />
              <p className="mt-4 text-gray-500 text-sm">Generating paper...</p>
            </div>
          ) : questions.length === 0 ? (
          /* Empty State */
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <div className="w-16 h-16 rounded-2xl bg-gray-100 flex items-center justify-center mb-4">
              <FileText className="w-8 h-8 text-gray-400" />
            </div>
            <h3 className="font-semibold text-gray-700 mb-2">No Preview Yet</h3>
            <p className="text-sm text-gray-500 max-w-xs">
              Configure your preferences and generate a paper to see the preview here.
            </p>
          </div>
        ) : (
          /* Preview Content */
          <div className="space-y-6">
            {/* Paper Header */}
            <div className="text-center pb-4 border-b border-gray-200">
              <h3 className="font-bold text-gray-900 text-lg">{subject}</h3>
              <p className="text-sm text-gray-500 mt-1">
                {questions.length} Questions • AI Generated
              </p>
            </div>

            {/* Sections */}
            {sections.map((section, sectionIndex) => (
              <div key={sectionIndex} className="space-y-4">
                <div className="flex items-center justify-between">
                  <h4 className="font-semibold text-gray-800">{section.title}</h4>
                  <span className="text-xs px-2 py-1 bg-indigo-50 text-indigo-600 rounded-full">
                    {section.marks}
                  </span>
                </div>

                <div className="space-y-3">
                  {section.questions.map((question, index) => (
                    <div
                      key={index}
                      className="p-4 bg-gray-50 rounded-xl border border-gray-100 hover:border-indigo-200 transition-colors"
                    >
                      <div className="flex items-start gap-3">
                        <span className="flex-shrink-0 w-6 h-6 bg-white border border-gray-200 rounded-full flex items-center justify-center text-xs font-medium text-gray-600">
                          {(sectionIndex === 0 ? 0 : sections[0].questions.length) + index + 1}
                        </span>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm text-gray-700 break-words break-all">
                            {question.question}
                          </p>
                          <span className="inline-block mt-2 text-xs px-2 py-0.5 bg-purple-50 text-purple-600 rounded">
                            {question.topic}
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}

            {/* Summary Card */}
            <div className="mt-6 p-4 bg-gradient-to-br from-indigo-50 to-purple-50 rounded-xl border border-indigo-100">
              <h4 className="font-semibold text-indigo-900 text-sm mb-3">Summary</h4>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-600">Total Questions:</span>
                  <span className="font-semibold text-gray-800">{questions.length}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Topics Covered:</span>
                  <span className="font-semibold text-gray-800">
                    {new Set(questions.map((q) => q.topic)).size}
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}
        </div>
      )}
    </aside>
  )
}
