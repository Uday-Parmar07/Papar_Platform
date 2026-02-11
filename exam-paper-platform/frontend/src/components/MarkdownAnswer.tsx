import React from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'

import 'katex/dist/katex.min.css'

interface MarkdownAnswerProps {
  content: string
}

export function MarkdownAnswer({ content }: MarkdownAnswerProps) {
  return (
    <div className="answer-text markdown-answer">
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[rehypeKatex]}
        linkTarget="_blank"
        skipHtml
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}
