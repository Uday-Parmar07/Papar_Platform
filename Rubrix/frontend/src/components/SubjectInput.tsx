import { useState, useRef, useEffect } from 'react'
import { Search, ChevronDown } from './icons'

interface SubjectInputProps {
  subjects: string[]
  selectedSubject: string
  onSelectSubject: (subject: string) => void
  loading?: boolean
}

export default function SubjectInput({
  subjects,
  selectedSubject,
  onSelectSubject,
  loading = false,
}: SubjectInputProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const dropdownRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const filteredSubjects = subjects.filter((subject) =>
    subject.toLowerCase().includes(searchQuery.toLowerCase())
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

  const handleSelect = (subject: string) => {
    onSelectSubject(subject)
    setSearchQuery('')
    setIsOpen(false)
  }

  return (
    <div className="space-y-2">
      <label className="block text-sm font-medium text-gray-700">Subject</label>
      <div className="relative" ref={dropdownRef}>
        <div
          className={`relative flex items-center border rounded-xl transition-all duration-200 ${
            isOpen
              ? 'border-indigo-500 ring-2 ring-indigo-100'
              : 'border-gray-200 hover:border-gray-300'
          }`}
        >
          <Search className="absolute left-4 w-5 h-5 text-gray-400" />
          <input
            ref={inputRef}
            type="text"
            placeholder={selectedSubject || 'Search for a subject...'}
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value)
              setIsOpen(true)
            }}
            onFocus={() => setIsOpen(true)}
            className="w-full pl-12 pr-10 py-3.5 bg-transparent text-gray-800 placeholder-gray-400 focus:outline-none rounded-xl"
          />
          <button
            type="button"
            onClick={() => {
              setIsOpen(!isOpen)
              if (!isOpen) inputRef.current?.focus()
            }}
            className="absolute right-3 p-1.5 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <ChevronDown className={`w-4 h-4 text-gray-500 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
          </button>
        </div>

        {isOpen && (
          <div className="absolute z-20 w-full mt-2 bg-white border border-gray-200 rounded-xl shadow-lg max-h-64 overflow-y-auto">
            {loading ? (
              <div className="px-4 py-8 text-center text-gray-500">
                <div className="animate-pulse">Loading subjects...</div>
              </div>
            ) : filteredSubjects.length === 0 ? (
              <div className="px-4 py-8 text-center text-gray-500">
                No subjects found
              </div>
            ) : (
              <div className="py-2">
                {filteredSubjects.map((subject) => (
                  <button
                    key={subject}
                    type="button"
                    onClick={() => handleSelect(subject)}
                    className={`w-full text-left px-4 py-3 transition-colors ${
                      selectedSubject === subject
                        ? 'bg-indigo-50 text-indigo-700 font-medium'
                        : 'text-gray-700 hover:bg-gray-50'
                    }`}
                  >
                    {subject}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Selected Subject Display */}
        {selectedSubject && !isOpen && (
          <div className="absolute inset-0 flex items-center pointer-events-none">
            <span className="pl-12 font-medium text-gray-800">{selectedSubject}</span>
          </div>
        )}
      </div>
    </div>
  )
}
