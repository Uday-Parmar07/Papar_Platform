import type { GeneratePaperQuestion } from '../types'
import ReactMarkdown from 'react-markdown'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import 'katex/dist/katex.min.css'

interface LatexPreviewProps {
  questions: GeneratePaperQuestion[]
  subject: string
}

export default function LatexPreview({ questions, subject }: LatexPreviewProps) {
  // Group questions into sections
  const sections = questions.length > 0
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
    <div className="bg-white min-h-screen p-8 font-serif">
      {/* Exam Paper Header */}
      <div className="border-b-2 border-black pb-4 mb-6">
        <h1 className="text-2xl font-bold text-center mb-2">{subject}</h1>
        <p className="text-center text-sm">
          GATE Examination • {questions.length} Questions • AI Generated
        </p>
      </div>

      {/* Instructions */}
      <div className="mb-6 p-4 bg-gray-50 border border-gray-300 rounded">
        <h3 className="font-bold mb-2">Instructions:</h3>
        <ul className="list-disc list-inside text-sm space-y-1">
          <li>All questions are compulsory.</li>
          <li>Answers should be brief and to the point.</li>
          <li>Use mathematical notation where appropriate.</li>
          <li>Show all steps in numerical problems.</li>
        </ul>
      </div>

      {/* Sections */}
      {sections.map((section, sectionIndex) => (
        <div key={sectionIndex} className="mb-8">
          <div className="flex items-center justify-between mb-4 border-b border-gray-300 pb-2">
            <h2 className="text-lg font-bold">{section.title}</h2>
            <span className="text-sm font-semibold">{section.marks}</span>
          </div>

          <div className="space-y-6">
            {section.questions.map((question, index) => (
              <div key={index} className="pl-4">
                <div className="flex items-start gap-3">
                  <span className="flex-shrink-0 font-bold">
                    {(sectionIndex === 0 ? 0 : sections[0].questions.length) + index + 1}.
                  </span>
                  <div className="flex-1">
                    <ReactMarkdown
                      remarkPlugins={[remarkMath]}
                      rehypePlugins={[rehypeKatex]}
                      className="prose prose-sm max-w-none"
                    >
                      {question.question}
                    </ReactMarkdown>
                    <div className="mt-2 text-xs text-gray-600 italic">
                      Topic: {question.topic}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}

      {/* Footer */}
      <div className="mt-12 pt-4 border-t border-gray-300 text-center text-sm text-gray-600">
        <p>*** End of Question Paper ***</p>
      </div>
    </div>
  )
}
