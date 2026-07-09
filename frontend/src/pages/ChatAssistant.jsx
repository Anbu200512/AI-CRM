import { useRef, useEffect, useState, useCallback } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { useNavigate } from 'react-router-dom'
import { sendChatMessage, fetchMessages, clearActiveConversation } from '../redux/slices/conversationsSlice'
import { clearChat } from '../redux/slices/chatSlice'
import ChatSidebar from '../components/chat/ChatSidebar'
import { AssistantMessage, TypingIndicator } from '../components/chat/AssistantMessage'
import {
  Bot, Send, Loader2, Menu, CheckCircle, ExternalLink,
  PenLine, FileText, MessageSquareText, ListTodo, Pencil,
  Search, History, Trash2, BarChart2,
} from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'

function formatTime(dateStr) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  const now = new Date()
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const diffDays = Math.floor((startOfToday - d) / (1000 * 60 * 60 * 24))
  if (diffDays <= 0) return 'Today'
  if (diffDays === 1) return 'Yesterday'
  return d.toLocaleDateString([], { day: 'numeric', month: 'short', year: 'numeric' })
}

function groupMessagesByDate(messages) {
  const groups = []
  let currentDate = null
  for (const msg of messages) {
    const date = formatDate(msg.created_at)
    if (date !== currentDate) {
      groups.push({ type: 'date', label: date })
      currentDate = date
    }
    groups.push({ type: 'message', ...msg })
  }
  return groups
}

function getInitials(name) {
  if (!name) return '?'
  return name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)
}

const quickActions = [
  { text: 'I met Dr. Priya at Apollo yesterday. We discussed Metformin for diabetes management for 30 minutes.', label: 'Log Interaction', icon: PenLine, color: 'blue' },
  { text: 'Summarize my last meeting with Dr. Sharma.', label: 'Summarize Meeting', icon: FileText, color: 'purple' },
  { text: 'Show my last 5 interactions.', label: 'Show History', icon: History, color: 'indigo' },
  { text: 'Search for interactions related to Metformin.', label: 'Search Interactions', icon: Search, color: 'teal' },
  { text: 'What follow-up actions do you recommend for Dr. Patel?', label: 'Follow-up Advice', icon: MessageSquareText, color: 'green' },
  { text: 'How many interactions did I log this week?', label: 'Dashboard Stats', icon: BarChart2, color: 'amber' },
  { text: 'Edit the last interaction: change interest level to High.', label: 'Edit Interaction', icon: Pencil, color: 'orange' },
  { text: 'Extract medical entities from: Patient has type 2 diabetes, prescribed Metformin 500mg.', label: 'Extract Entities', icon: ListTodo, color: 'rose' },
]

const colorMap = {
  blue: 'bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-300',
  purple: 'bg-purple-50 dark:bg-purple-900/20 text-purple-600 dark:text-purple-300',
  indigo: 'bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600 dark:text-indigo-300',
  teal: 'bg-teal-50 dark:bg-teal-900/20 text-teal-600 dark:text-teal-300',
  green: 'bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-300',
  amber: 'bg-amber-50 dark:bg-amber-900/20 text-amber-600 dark:text-amber-300',
  orange: 'bg-orange-50 dark:bg-orange-900/20 text-orange-600 dark:text-orange-300',
  rose: 'bg-rose-50 dark:bg-rose-900/20 text-rose-600 dark:text-rose-300',
}

export default function ChatAssistant() {
  const dispatch = useDispatch()
  const navigate = useNavigate()
  const { conversations, activeConversationId, messages, sending } = useSelector((state) => state.conversations)
  const user = useSelector((state) => state.auth.user)
  const [input, setInput] = useState('')
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [successMsg, setSuccessMsg] = useState(null)
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    const lastConv = localStorage.getItem('lastConversationId')
    if (lastConv && !activeConversationId && messages.length === 0) {
      dispatch(fetchMessages(lastConv))
    }
  }, [])

  useEffect(() => {
    if (activeConversationId) {
      localStorage.setItem('lastConversationId', activeConversationId)
    }
  }, [activeConversationId])

  const handleNewChat = useCallback(() => {
    dispatch(clearActiveConversation())
    dispatch(clearChat())
    localStorage.removeItem('lastConversationId')
    setInput('')
    setSuccessMsg(null)
    inputRef.current?.focus()
  }, [dispatch])

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!input.trim() || sending) return
    const userMsg = input.trim()
    setInput('')
    setSuccessMsg(null)
    dispatch({ type: 'conversations/addMessageLocally', payload: { role: 'user', content: userMsg, id: Date.now(), created_at: new Date().toISOString() } })
    const result = await dispatch(sendChatMessage({ message: userMsg, conversationId: activeConversationId }))
    if (result.meta.requestStatus === 'fulfilled') {
      const toolUsed = result.payload.tool_used
      if (toolUsed === 'log_interaction' && result.payload.response?.includes('Logged Successfully')) {
        setSuccessMsg(result.payload.response)
      }
    } else {
      dispatch({ type: 'conversations/addMessageLocally', payload: { role: 'assistant', content: 'Sorry, I encountered an error. Please try again.', id: Date.now() + 1, created_at: new Date().toISOString() } })
    }
  }

  const grouped = groupMessagesByDate(messages)
  const activeConv = conversations.find((c) => c.id === activeConversationId)
  const isNewChat = !activeConversationId
  const userInitials = getInitials(user?.name)

  return (
    <div className="flex bg-white dark:bg-gray-900 rounded-2xl border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden" style={{ height: 'calc(100vh - 7rem)' }}>
      <ChatSidebar isOpen={sidebarOpen} onToggle={() => setSidebarOpen(false)} />

      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700 flex-shrink-0 flex items-center gap-2">
          {!sidebarOpen && (
            <button onClick={() => setSidebarOpen(true)} className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500" title="Open sidebar">
              <Menu size={18} />
            </button>
          )}
          <div className="flex-1 min-w-0 text-center sm:text-left">
            <h2 className="text-sm font-semibold text-gray-900 dark:text-white truncate">
              {isNewChat ? 'AI CRM Assistant' : activeConv?.title || 'Chat'}
            </h2>
            <p className="text-[11px] text-gray-500">Pharmaceutical HCP CRM · Powered by Groq</p>
          </div>
          <button onClick={handleNewChat} className="text-sm px-3 py-1.5 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 flex-shrink-0 transition-colors">
            + New Chat
          </button>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto scrollbar-hide px-4 py-4 space-y-3">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full max-w-2xl mx-auto">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary-400 to-primary-600 text-white flex items-center justify-center shadow-lg mb-5">
                <Bot size={32} />
              </div>
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">AI CRM Assistant</h2>
              <p className="text-sm text-gray-500 dark:text-gray-400 text-center leading-relaxed mb-8 max-w-md">
                Your intelligent Pharmaceutical CRM assistant. Log meetings, search records, analyze interactions, and manage follow-ups — all through natural conversation.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full">
                {quickActions.map((item, i) => (
                  <button
                    key={i}
                    onClick={() => { setInput(item.text); inputRef.current?.focus() }}
                    className="flex items-center gap-3 px-3.5 py-3 rounded-xl border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 hover:border-primary-300 dark:hover:border-primary-700 transition-all text-left group"
                  >
                    <div className={`p-2 rounded-lg flex-shrink-0 ${colorMap[item.color]}`}>
                      <item.icon size={14} />
                    </div>
                    <span className="text-xs font-medium text-gray-700 dark:text-gray-300 group-hover:text-gray-900 dark:group-hover:text-white">{item.label}</span>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <>
              {grouped.map((item, i) => {
                if (item.type === 'date') {
                  return (
                    <div key={`date-${i}`} className="flex justify-center py-1">
                      <span className="text-[11px] text-gray-400 bg-gray-100 dark:bg-gray-800 px-2.5 py-0.5 rounded-full">{item.label}</span>
                    </div>
                  )
                }
                const isUser = item.role === 'user'
                return (
                  <motion.div key={item.id || i} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className={`flex gap-2.5 ${isUser ? 'justify-end' : ''}`}>
                    {!isUser && (
                      <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-primary-400 to-primary-600 text-white flex items-center justify-center flex-shrink-0 mt-0.5 shadow-sm">
                        <Bot size={17} />
                      </div>
                    )}
                    <div className={`max-w-[78%] ${isUser ? 'order-first' : ''}`}>
                      <div className={`px-4 py-3 text-sm leading-relaxed ${
                        isUser
                          ? 'bg-primary-600 text-white rounded-2xl rounded-br-sm whitespace-pre-wrap'
                          : 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-white rounded-2xl rounded-bl-sm'
                      }`}>
                        {isUser ? item.content : <AssistantMessage content={item.content} />}
                      </div>
                      <p className={`text-[11px] text-gray-400 mt-0.5 ${isUser ? 'text-right' : 'text-left'}`}>
                        {formatTime(item.created_at)}
                      </p>
                    </div>
                    {isUser && (
                      <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-gray-400 to-gray-600 text-white flex items-center justify-center flex-shrink-0 mt-0.5 shadow-sm text-xs font-semibold">
                        {userInitials}
                      </div>
                    )}
                  </motion.div>
                )
              })}

              <AnimatePresence>
                {successMsg && (
                  <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="flex justify-center py-2">
                    <div className="flex items-center gap-2.5 px-4 py-2.5 rounded-xl bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800">
                      <CheckCircle size={18} className="text-green-600 dark:text-green-400" />
                      <span className="text-sm font-medium text-green-700 dark:text-green-300">Interaction logged successfully</span>
                      <button onClick={() => navigate('/history')} className="ml-1 text-xs px-2.5 py-1 rounded-lg bg-green-600 hover:bg-green-700 text-white transition-colors flex items-center gap-1">
                        View Record <ExternalLink size={12} />
                      </button>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              {sending && <TypingIndicator />}
              <div ref={messagesEndRef} />
            </>
          )}
        </div>

        {/* Input */}
        <div className="px-4 py-3 border-t border-gray-200 dark:border-gray-700 flex-shrink-0">
          <form onSubmit={handleSubmit} className="flex gap-2">
            <input
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              className="flex-1 px-4 py-2.5 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-sm text-gray-900 dark:text-white placeholder-gray-400 focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none transition-colors"
              placeholder="Log a meeting, search records, ask about your CRM data..."
              disabled={sending}
            />
            <button type="submit" disabled={sending || !input.trim()} className="px-4 py-2.5 rounded-xl bg-primary-600 hover:bg-primary-700 text-white text-sm disabled:opacity-40 disabled:cursor-not-allowed transition-colors flex-shrink-0 shadow-sm">
              {sending ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
