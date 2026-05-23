import { useState, useRef, useEffect } from 'react'
import { Plus, X, Search } from './icons'

interface TopicSelectorProps {
  availableTopics: string[]
  selectedTopics: string[]
  onTopicToggle: (topic: string) => void
  loading?: boolean
  disabled?: boolean
}

export default function TopicSelector({
  availableTopics,
  selectedTopics,
  onTopicToggle,
  loading = false,
  disabled = false,
}: TopicSelectorProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const dropdownRef = useRef<HTMLDivElement>(null)

  const unselectedTopics = availableTopics.filter(
    (topic) =>
      !selectedTopics.includes(topic) &&
      topic.toLowerCase().includes(searchQuery.toLowerCase())
  )

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleAddTopic = (topic: string) => {
    onTopicToggle(topic)
    setSearchQuery('')
  }

  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium text-gray-700">Topics</label>

      {/* Selected Topics Chips */}
      <div className="flex flex-wrap gap-2 min-h-[44px]">
        {selectedTopics.map((topic) => (
          <span
            key={topic}
            className="inline-flex items-center gap-2 px-3 py-2 bg-gradient-to-r from-indigo-50 to-purple-50 border border-indigo-200 text-indigo-700 rounded-lg text-sm font-medium group transition-all hover:shadow-sm"
          >
            {topic}
            <button
              type="button"
              onClick={() => onTopicToggle(topic)}
              className="p-0.5 hover:bg-indigo-200 rounded-full transition-colors"
              aria-label={`Remove ${topic}`}
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </span>
        ))}

        {selectedTopics.length === 0 && !disabled && (
          <span className="text-gray-400 text-sm py-2">
            No topics selected. Add topics to continue.
          </span>
        )}
      </div>

      {/* Add Topic Dropdown */}
      <div className="relative" ref={dropdownRef}>
        <button
          type="button"
          onClick={() => !disabled && setIsOpen(!isOpen)}
          disabled={disabled}
          className={`inline-flex items-center gap-2 px-4 py-2.5 border-2 border-dashed rounded-xl text-sm font-medium transition-all ${
            disabled
              ? 'border-gray-200 text-gray-400 cursor-not-allowed'
              : 'border-indigo-300 text-indigo-600 hover:border-indigo-400 hover:bg-indigo-50'
          }`}
        >
          <Plus className="w-4 h-4" />
          Add Topic
        </button>

        {isOpen && !disabled && (
          <div className="absolute z-20 w-80 mt-2 bg-white border border-gray-200 rounded-xl shadow-lg">
            {/* Search Input */}
            <div className="p-3 border-b border-gray-100">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search topics..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  autoFocus
                />
              </div>
            </div>

            {/* Topics List */}
            <div className="max-h-64 overflow-y-auto py-2">
              {loading ? (
                <div className="px-4 py-8 text-center text-gray-500">
                  <div className="animate-pulse">Loading topics...</div>
                </div>
              ) : unselectedTopics.length === 0 ? (
                <div className="px-4 py-8 text-center text-gray-500">
                  {availableTopics.length === 0
                    ? 'Select a subject first'
                    : searchQuery
                    ? 'No matching topics'
                    : 'All topics selected'}
                </div>
              ) : (
                unselectedTopics.map((topic) => (
                  <button
                    key={topic}
                    type="button"
                    onClick={() => handleAddTopic(topic)}
                    className="w-full text-left px-4 py-2.5 text-sm text-gray-700 hover:bg-indigo-50 hover:text-indigo-700 transition-colors"
                  >
                    {topic}
                  </button>
                ))
              )}
            </div>

            {/* Select All Option */}
            {unselectedTopics.length > 0 && !loading && (
              <div className="p-3 border-t border-gray-100">
                <button
                  type="button"
                  onClick={() => {
                    unselectedTopics.forEach(handleAddTopic)
                    setIsOpen(false)
                  }}
                  className="w-full py-2 text-sm font-medium text-indigo-600 hover:bg-indigo-50 rounded-lg transition-colors"
                >
                  Select all {unselectedTopics.length} topics
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
