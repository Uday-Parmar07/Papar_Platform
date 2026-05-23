import { FileText, Lightbulb, Clock, ChevronLeft, ChevronRight } from './icons'

interface HistoryItem {
  id: string
  subject: string
  questionCount: number
  timestamp: string
  isActive?: boolean
}

interface SidebarProps {
  history: HistoryItem[]
  onSelectHistory: (id: string) => void
  collapsed?: boolean
  onToggleCollapse?: () => void
}

export default function Sidebar({ history, onSelectHistory, collapsed = false, onToggleCollapse }: SidebarProps) {
  return (
    <aside className={`hidden lg:flex flex-col bg-white border-r border-gray-200 h-screen sticky top-0 transition-all duration-300 ${collapsed ? 'w-16' : 'w-72'}`}>
      {/* Header */}
      <div className="p-4 border-b border-gray-100 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center flex-shrink-0">
            <FileText className="w-5 h-5 text-white" />
          </div>
          {!collapsed && (
            <div>
              <h1 className="font-bold text-gray-900 text-lg">PaperGen</h1>
              <p className="text-xs text-gray-500">AI Question Generator</p>
            </div>
          )}
        </div>
        {onToggleCollapse && (
          <button
            onClick={onToggleCollapse}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors flex-shrink-0"
            title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {collapsed ? (
              <ChevronRight className="w-5 h-5 text-gray-600" />
            ) : (
              <ChevronLeft className="w-5 h-5 text-gray-600" />
            )}
          </button>
        )}
      </div>

      {/* Recent History */}
      {!collapsed && (
        <div className="flex-1 overflow-y-auto p-4">
          <div className="flex items-center gap-2 mb-4 px-2">
            <Clock className="w-4 h-4 text-gray-400" />
            <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide">
              Recent History
            </h2>
          </div>

          <div className="space-y-2">
            {history.length === 0 ? (
              <p className="text-sm text-gray-400 px-2 py-4 text-center">
                No papers generated yet
              </p>
            ) : (
              history.map((item) => (
                <button
                  key={item.id}
                  onClick={() => onSelectHistory(item.id)}
                  className={`w-full text-left px-4 py-3 rounded-xl transition-all duration-200 group ${
                    item.isActive
                      ? 'bg-gradient-to-r from-indigo-50 to-purple-50 border border-indigo-200 shadow-sm'
                      : 'hover:bg-gray-50 border border-transparent'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <p className={`font-medium truncate ${
                        item.isActive ? 'text-indigo-700' : 'text-gray-800'
                      }`}>
                        {item.subject}
                      </p>
                      <p className="text-xs text-gray-500 mt-1">
                        {item.questionCount} Questions • {item.timestamp}
                      </p>
                    </div>
                    {item.isActive && (
                      <div className="w-2 h-2 rounded-full bg-indigo-500 mt-2 ml-2 flex-shrink-0" />
                    )}
                  </div>
                </button>
              ))
            )}
          </div>
        </div>
      )}

      {/* Pro Tip Card */}
      {!collapsed && (
        <div className="p-4">
          <div className="bg-gradient-to-br from-amber-50 to-orange-50 border border-amber-200 rounded-2xl p-4">
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-lg bg-amber-100 flex items-center justify-center flex-shrink-0">
                <Lightbulb className="w-4 h-4 text-amber-600" />
              </div>
              <div>
                <h3 className="font-semibold text-amber-900 text-sm">Pro Tip</h3>
                <p className="text-xs text-amber-700 mt-1 leading-relaxed">
                  Select multiple topics to create a comprehensive exam paper covering various concepts.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </aside>
  )
}
