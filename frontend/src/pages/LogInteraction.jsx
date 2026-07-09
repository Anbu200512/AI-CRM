import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useDispatch } from 'react-redux'
import { useForm } from 'react-hook-form'
import { motion, AnimatePresence } from 'framer-motion'
import toast from 'react-hot-toast'
import { createInteraction } from '../redux/slices/interactionSlice'
import { sendMessage } from '../redux/slices/chatSlice'
import { INTERACTION_TYPES, INTEREST_LEVELS } from '../constants'
import { AssistantMessage, TypingIndicator } from '../components/chat/AssistantMessage'
import {
  MessageSquareText, FormInput, Send, Bot, User, CheckCircle, ExternalLink,
  PenLine, FileText, History, Search, BarChart2,
} from 'lucide-react'

const quickActions = [
  { text: 'I met Dr. Priya at Apollo yesterday. We discussed Metformin for diabetes management for 30 minutes.', label: 'Log Meeting', icon: PenLine, color: 'blue' },
  { text: 'Summarize my last meeting with Dr. Sharma.', label: 'Summarize', icon: FileText, color: 'purple' },
  { text: 'Show my last 5 interactions.', label: 'Show History', icon: History, color: 'indigo' },
  { text: 'Search for interactions related to Metformin.', label: 'Search', icon: Search, color: 'teal' },
  { text: 'How many interactions did I log this week?', label: 'Stats', icon: BarChart2, color: 'amber' },
]

const colorMap = {
  blue: 'bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-300',
  purple: 'bg-purple-50 dark:bg-purple-900/20 text-purple-600 dark:text-purple-300',
  indigo: 'bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600 dark:text-indigo-300',
  teal: 'bg-teal-50 dark:bg-teal-900/20 text-teal-600 dark:text-teal-300',
  amber: 'bg-amber-50 dark:bg-amber-900/20 text-amber-600 dark:text-amber-300',
}

function formatTime(dateStr) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

export default function LogInteraction() {
  const [activeTab, setActiveTab] = useState('form')
  const navigate = useNavigate()
  const dispatch = useDispatch()
  const { register, handleSubmit, formState: { errors }, reset } = useForm()
  const [chatInput, setChatInput] = useState('')
  const [chatLoading, setChatLoading] = useState(false)
  const [chatMessages, setChatMessages] = useState([
    { role: 'assistant', content: 'Hello! I am your AI assistant. Describe your HCP interaction and I will log it for you.\n\nFor example: "I met Dr. Ravi at Apollo Hospital today. We discussed insulin. Doctor showed strong interest. Follow up next Monday."', created_at: new Date().toISOString() }
  ])
  const [successMsg, setSuccessMsg] = useState(null)
  const messagesEndRef = useRef(null)
  const chatInputRef = useRef(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatMessages, chatLoading])

  const onSubmitForm = async (data) => {
    try {
      await dispatch(createInteraction({ ...data, interaction_date: data.interaction_date || new Date().toISOString().split('T')[0] })).unwrap()
      toast.success('Interaction logged successfully!')
      reset()
      navigate('/history')
    } catch (err) {
      toast.error(err || 'Failed to log interaction')
    }
  }

  const handleChatSubmit = async (e) => {
    e.preventDefault()
    if (!chatInput.trim()) return
    const userMsg = chatInput
    setChatInput('')
    setSuccessMsg(null)
    setChatMessages((prev) => [...prev, { role: 'user', content: userMsg, created_at: new Date().toISOString() }])
    setChatLoading(true)
    try {
      const result = await dispatch(sendMessage(userMsg)).unwrap()
      setChatMessages((prev) => [...prev, { role: 'assistant', content: result.response, created_at: new Date().toISOString() }])
      if (result.tool_used === 'log_interaction' && result.response?.includes('Logged Successfully')) {
        setSuccessMsg(result.response)
      }
    } catch (err) {
      setChatMessages((prev) => [...prev, { role: 'assistant', content: 'Sorry, I encountered an error. Please try again.', created_at: new Date().toISOString() }])
    } finally {
      setChatLoading(false)
    }
  }

  const tabs = [
    { id: 'form', label: 'Structured Form', icon: FormInput },
    { id: 'chat', label: 'AI Conversation', icon: MessageSquareText },
  ]

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Log Interaction</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400">Record a new HCP interaction</p>
      </div>

      <div className="flex gap-1 p-1 bg-gray-100 dark:bg-gray-800 rounded-xl w-fit">
        {tabs.map(({ id, label, icon: Icon }) => (
          <button key={id} onClick={() => setActiveTab(id)} className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${activeTab === id ? 'tab-active shadow-sm' : 'tab-inactive'}`}>
            <Icon size={18} />
            {label}
          </button>
        ))}
      </div>

      <AnimatePresence mode="wait">
        {activeTab === 'form' ? (
          <motion.form key="form" initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} onSubmit={handleSubmit(onSubmitForm)} className="card p-6 space-y-5">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Doctor Name *</label>
                <input {...register('doctor_name', { required: 'Doctor name is required' })} className="input-field" placeholder="Dr. Name" />
                {errors.doctor_name && <p className="text-xs text-red-500 mt-1">{errors.doctor_name.message}</p>}
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Hospital</label>
                <input {...register('hospital')} className="input-field" placeholder="Hospital name" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Speciality</label>
                <input {...register('speciality')} className="input-field" placeholder="Cardiology, etc." />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Interaction Date *</label>
                <input type="date" {...register('interaction_date', { required: true })} className="input-field" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Meeting Duration (minutes)</label>
                <input type="number" {...register('duration')} className="input-field" placeholder="30" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Interaction Type</label>
                <select {...register('interaction_type')} className="input-field">
                  {INTERACTION_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Products Discussed</label>
                <input {...register('products')} className="input-field" placeholder="e.g. Insulin, Metformin" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Competitor Products</label>
                <input {...register('competitors')} className="input-field" placeholder="e.g. Competitor A" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Interest Level</label>
                <select {...register('interest_level')} className="input-field">
                  {INTEREST_LEVELS.map((l) => <option key={l.value} value={l.value}>{l.label}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Follow-up Date</label>
                <input type="date" {...register('follow_up_date')} className="input-field" />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Discussion Notes</label>
              <textarea {...register('discussion')} rows={4} className="input-field resize-none" placeholder="Describe the interaction..." />
            </div>
            <div className="flex gap-3 pt-2">
              <button type="submit" className="btn-primary">Save Interaction</button>
              <button type="button" onClick={() => reset()} className="btn-secondary">Reset</button>
            </div>
          </motion.form>
        ) : (
          <motion.div key="chat" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 20 }} className="card p-6">
            <div className="h-[500px] overflow-y-auto space-y-4 mb-4 scrollbar-thin">
              {chatMessages.length === 1 ? (
                <div className="flex flex-col items-center justify-center h-full max-w-md mx-auto">
                  <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-primary-400 to-primary-600 text-white flex items-center justify-center shadow-lg mb-4">
                    <Bot size={28} />
                  </div>
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-1">Log Interaction via AI</h3>
                  <p className="text-xs text-gray-500 dark:text-gray-400 text-center leading-relaxed mb-6">
                    Describe your meeting and I will extract and log it for you.
                  </p>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full">
                    {quickActions.map((item, i) => (
                      <button
                        key={i}
                        onClick={() => { setChatInput(item.text); chatInputRef.current?.focus() }}
                        className="flex items-center gap-3 px-3 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 hover:border-primary-300 dark:hover:border-primary-700 transition-all text-left group"
                      >
                        <div className={`p-1.5 rounded-lg flex-shrink-0 ${colorMap[item.color]}`}>
                          <item.icon size={13} />
                        </div>
                        <span className="text-xs font-medium text-gray-700 dark:text-gray-300 group-hover:text-gray-900 dark:group-hover:text-white">{item.label}</span>
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                <>
                  {chatMessages.map((msg, i) => (
                    <motion.div key={i} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className={`flex gap-2.5 ${msg.role === 'user' ? 'justify-end' : ''}`}>
                      {msg.role === 'assistant' && (
                        <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-primary-400 to-primary-600 text-white flex items-center justify-center flex-shrink-0 mt-0.5 shadow-sm">
                          <Bot size={17} />
                        </div>
                      )}
                      <div className={`max-w-[78%] ${msg.role === 'user' ? 'order-first' : ''}`}>
                        <div className={`px-4 py-3 text-sm leading-relaxed ${
                          msg.role === 'user'
                            ? 'bg-primary-600 text-white rounded-2xl rounded-br-sm whitespace-pre-wrap'
                            : 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-white rounded-2xl rounded-bl-sm'
                        }`}>
                          {msg.role === 'user' ? msg.content : <AssistantMessage content={msg.content} />}
                        </div>
                        <p className={`text-[11px] text-gray-400 mt-0.5 ${msg.role === 'user' ? 'text-right' : 'text-left'}`}>
                          {formatTime(msg.created_at)}
                        </p>
                      </div>
                      {msg.role === 'user' && (
                        <div className="w-8 h-8 rounded-xl bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-300 flex items-center justify-center flex-shrink-0 mt-0.5">
                          <User size={18} />
                        </div>
                      )}
                    </motion.div>
                  ))}

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

                  {chatLoading && <TypingIndicator />}
                  <div ref={messagesEndRef} />
                </>
              )}
            </div>
            <form onSubmit={handleChatSubmit} className="flex gap-2">
              <input
                ref={chatInputRef}
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                className="input-field flex-1"
                placeholder="Describe your HCP interaction..."
                disabled={chatLoading}
              />
              <button type="submit" disabled={chatLoading || !chatInput.trim()} className="btn-primary px-4">
                <Send size={18} />
              </button>
            </form>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
