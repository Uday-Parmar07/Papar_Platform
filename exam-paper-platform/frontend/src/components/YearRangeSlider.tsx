import { useState, useCallback, useRef, useEffect } from 'react'

interface YearRangeSliderProps {
  minYear: number
  maxYear: number
  startYear: number
  endYear: number
  onRangeChange: (start: number, end: number) => void
}

export default function YearRangeSlider({
  minYear,
  maxYear,
  startYear,
  endYear,
  onRangeChange,
}: YearRangeSliderProps) {
  const [localStart, setLocalStart] = useState(startYear)
  const [localEnd, setLocalEnd] = useState(endYear)
  const [dragging, setDragging] = useState<'start' | 'end' | null>(null)
  const trackRef = useRef<HTMLDivElement>(null)

  const range = maxYear - minYear
  const startPercent = ((localStart - minYear) / range) * 100
  const endPercent = ((localEnd - minYear) / range) * 100

  const updateValue = useCallback(
    (clientX: number, type: 'start' | 'end') => {
      if (!trackRef.current) return
      
      const rect = trackRef.current.getBoundingClientRect()
      const percent = Math.max(0, Math.min(100, ((clientX - rect.left) / rect.width) * 100))
      const year = Math.round(minYear + (percent / 100) * range)

      if (type === 'start') {
        const newStart = Math.min(year, localEnd - 1)
        setLocalStart(Math.max(minYear, newStart))
      } else {
        const newEnd = Math.max(year, localStart + 1)
        setLocalEnd(Math.min(maxYear, newEnd))
      }
    },
    [minYear, maxYear, range, localStart, localEnd]
  )

  useEffect(() => {
    if (!dragging) return

    const handleMouseMove = (e: MouseEvent) => {
      updateValue(e.clientX, dragging)
    }

    const handleMouseUp = () => {
      setDragging(null)
      onRangeChange(localStart, localEnd)
    }

    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)

    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }
  }, [dragging, updateValue, localStart, localEnd, onRangeChange])

  useEffect(() => {
    setLocalStart(startYear)
    setLocalEnd(endYear)
  }, [startYear, endYear])

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <label className="block text-sm font-medium text-gray-700">Year Range</label>
        <div className="flex items-center gap-2">
          <span className="px-3 py-1.5 bg-gradient-to-r from-indigo-50 to-purple-50 border border-indigo-200 rounded-lg text-sm font-semibold text-indigo-700">
            {localStart}
          </span>
          <span className="text-gray-400">—</span>
          <span className="px-3 py-1.5 bg-gradient-to-r from-indigo-50 to-purple-50 border border-indigo-200 rounded-lg text-sm font-semibold text-indigo-700">
            {localEnd}
          </span>
        </div>
      </div>

      {/* Slider Track */}
      <div className="relative pt-2 pb-4">
        <div
          ref={trackRef}
          className="relative h-2 bg-gray-200 rounded-full cursor-pointer"
          onClick={(e) => {
            const rect = trackRef.current?.getBoundingClientRect()
            if (!rect) return
            const percent = ((e.clientX - rect.left) / rect.width) * 100
            const year = Math.round(minYear + (percent / 100) * range)
            
            // Determine which handle to move
            const distToStart = Math.abs(year - localStart)
            const distToEnd = Math.abs(year - localEnd)
            
            if (distToStart < distToEnd) {
              setLocalStart(Math.min(year, localEnd - 1))
              onRangeChange(Math.min(year, localEnd - 1), localEnd)
            } else {
              setLocalEnd(Math.max(year, localStart + 1))
              onRangeChange(localStart, Math.max(year, localStart + 1))
            }
          }}
        >
          {/* Active Range */}
          <div
            className="absolute h-full bg-gradient-to-r from-indigo-500 to-purple-500 rounded-full"
            style={{
              left: `${startPercent}%`,
              width: `${endPercent - startPercent}%`,
            }}
          />

          {/* Start Handle */}
          <div
            className={`absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-5 h-5 bg-white border-2 border-indigo-500 rounded-full shadow-md cursor-grab hover:scale-110 transition-transform ${
              dragging === 'start' ? 'scale-110 cursor-grabbing ring-4 ring-indigo-100' : ''
            }`}
            style={{ left: `${startPercent}%` }}
            onMouseDown={(e) => {
              e.preventDefault()
              setDragging('start')
            }}
          />

          {/* End Handle */}
          <div
            className={`absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-5 h-5 bg-white border-2 border-purple-500 rounded-full shadow-md cursor-grab hover:scale-110 transition-transform ${
              dragging === 'end' ? 'scale-110 cursor-grabbing ring-4 ring-purple-100' : ''
            }`}
            style={{ left: `${endPercent}%` }}
            onMouseDown={(e) => {
              e.preventDefault()
              setDragging('end')
            }}
          />
        </div>

        {/* Year Labels */}
        <div className="flex justify-between mt-2 text-xs text-gray-500">
          <span>{minYear}</span>
          <span>{maxYear}</span>
        </div>
      </div>
    </div>
  )
}
