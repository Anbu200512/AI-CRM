import { useEffect, useMemo } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import {
  fetchConversations,
  deleteConversation,
  fetchMessages,
  clearActiveConversation,
} from '../../redux/slices/conversationsSlice'
import { clearChat } from '../../redux/slices/chatSlice'
import { Plus, MessageSquare, Trash2, X, History, Clock, CalendarDays } from 'lucide-react'

function getGroup(dateStr) {
  if (!dateStr) return 'Older'
  const d = new Date(dateStr)
  const now = new Date()
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const diffDays = Math.floor((startOfToday - d) / (1000 * 60 * 60 * 24))
  if (diffDays < 0) return 'Today'
  if (diffDays === 0) return 'Today'
  if (diffDays === 1) return 'Yesterday'
  if (diffDays <= 7) return 'Last 7 Days'
  return 'Older'
}

const groupMeta = {
  'Today': { icon: Clock, label: 'Today' },
  'Yesterday': { icon: Clock, label: 'Yesterday' },
  'Last 7 Days': { icon: CalendarDays, label: 'Last 7 Days' },
  'Older': { icon: History, label: 'Older' },
}

function formatTime(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  const now = new Date()
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const diffDays = Math.floor((startOfToday - d) / (1000 * 60 * 60 * 24))
  if (diffDays <= 0) return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  if (diffDays === 1) return 'Yesterday'
  if (diffDays < 7) return d.toLocaleDateString([], { weekday: 'short' })
  return d.toLocaleDateString([], { day: 'numeric', month: 'short' })
}

export default function ChatSidebar({ isOpen, onToggle }) {
  const dispatch = useDispatch()
  const { conversations, activeConversationId, loading } = useSelector((state) => state.conversations)

  useEffect(() => {
    if (isOpen) dispatch(fetchConversations())
  }, [isOpen, dispatch])

  const grouped = useMemo(() => {
    const groups = { 'Today': [], 'Yesterday': [], 'Last 7 Days': [], 'Older': [] }
    for (const conv of conversations) {
      const g = getGroup(conv.updated_at)
      if (groups[g]) groups[g].push(conv)
    }
    return groups
  }, [conversations])

  const handleNewChat = () => {
    dispatch(clearActiveConversation())
    dispatch(clearChat())
  }

  const handleSelect = (convId) => {
    dispatch(fetchMessages(convId))
  }

  const handleDelete = (e, convId) => {
    e.stopPropagation()
    if (activeConversationId === convId) {
      dispatch(clearActiveConversation())
      dispatch(clearChat())
    }
    dispatch(deleteConversation(convId))
  }

  const hasConversations = Object.values(grouped).some((g) => g.length > 0)
  const totalCount = conversations.length

  return (
    <div className={`w-72 flex-shrink-0 h-full bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800 flex flex-col transition-all duration-300 ${isOpen ? 'block' : 'hidden'}`}>
      <div className="p-3">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-sm font-semibold text-gray-900 dark:text-white">Conversations</h2>
          <div className="flex items-center gap-1">
            {totalCount > 0 && (
              <span className="text-[11px] text-gray-400 mr-1">{totalCount}</span>
            )}
            <button onClick={onToggle} className="p-1 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-800 text-gray-500" title="Close sidebar">
              <X size={18} />
            </button>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto scrollbar-hide py-2">
        {loading && conversations.length === 0 ? (
          <div className="text-center py-8 text-sm text-gray-400">Loading...</div>
        ) : !hasConversations ? (
          <div className="text-center py-8 text-sm text-gray-400">No conversations yet</div>
        ) : (
          Object.entries(groupMeta).map(([key, { icon: Icon, label }]) => {
            const items = grouped[key]
            if (items.length === 0) return null
            return (
              <div key={key} className="mb-1">
                <div className="flex items-center gap-1.5 px-3 py-1.5">
                  <Icon size={12} className="text-gray-400" />
                  <span className="text-[11px] font-medium text-gray-400 uppercase tracking-wider">{label}</span>
                </div>
                {items.map((conv) => (
                  <button
                    key={conv.id}
                    onClick={() => handleSelect(conv.id)}
                    className={`w-full flex items-start gap-2 px-3 py-2.5 text-left text-sm transition-colors group hover:bg-gray-100 dark:hover:bg-gray-800 ${
                      activeConversationId === conv.id
                        ? 'bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-300'
                        : 'text-gray-700 dark:text-gray-300'
                    }`}
                  >
                    <MessageSquare size={15} className="mt-0.5 flex-shrink-0 opacity-50" />
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-[13px] truncate">{conv.title || conv.last_message?.slice(0, 40) || 'New Conversation'}</p>
                      {conv.last_message && (
                        <p className="text-[11px] text-gray-400 dark:text-gray-500 truncate mt-0.5">{conv.last_message}</p>
                      )}
                    </div>
                    <div className="flex items-center gap-1 flex-shrink-0">
                      <span className="text-[10px] text-gray-400 mt-0.5">{formatTime(conv.updated_at)}</span>
                      <button
                        onClick={(e) => handleDelete(e, conv.id)}
                        className="p-0.5 rounded opacity-0 group-hover:opacity-100 hover:bg-red-100 dark:hover:bg-red-900/30 text-gray-400 hover:text-red-500 transition-all"
                      >
                        <Trash2 size={12} />
                      </button>
                    </div>
                  </button>
                ))}
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
