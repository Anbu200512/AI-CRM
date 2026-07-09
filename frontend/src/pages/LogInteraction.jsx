import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useDispatch } from 'react-redux'
import { useForm } from 'react-hook-form'
import { motion, AnimatePresence } from 'framer-motion'
import toast from 'react-hot-toast'
import { createInteraction } from '../redux/slices/interactionSlice'
import { sendMessage } from '../redux/slices/chatSlice'
import { INTERACTION_TYPES, INTEREST_LEVELS } from '../constants'
import { MessageSquareText, FormInput, Send, Bot, User, Loader2 } from 'lucide-react'

export default function LogInteraction() {
  const [activeTab, setActiveTab] = useState('form')
  const navigate = useNavigate()
  const dispatch = useDispatch()
  const { register, handleSubmit, formState: { errors }, reset } = useForm()
  const [chatInput, setChatInput] = useState('')
  const [chatLoading, setChatLoading] = useState(false)
  const [chatMessages, setChatMessages] = useState([
    { role: 'assistant', content: 'Hello! I am your AI assistant. Describe your HCP interaction and I will log it for you. For example: "I met Dr. Ravi at Apollo Hospital today. We discussed insulin. Doctor showed strong interest. Follow up next Monday."' }
  ])

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
    setChatMessages((prev) => [...prev, { role: 'user', content: userMsg }])
    setChatLoading(true)
    try {
      const result = await dispatch(sendMessage(userMsg)).unwrap()
      setChatMessages((prev) => [...prev, { role: 'assistant', content: result.response }])
      toast.success('Interaction logged via AI!')
    } catch (err) {
      setChatMessages((prev) => [...prev, { role: 'assistant', content: 'Sorry, I encountered an error. Please try again.' }])
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
            <div className="h-[400px] overflow-y-auto space-y-4 mb-4 scrollbar-thin">
              {chatMessages.map((msg, i) => (
                <div key={i} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : ''}`}>
                  {msg.role === 'assistant' && (
                    <div className="w-8 h-8 rounded-xl bg-primary-100 dark:bg-primary-900/30 text-primary-600 dark:text-primary-300 flex items-center justify-center flex-shrink-0">
                      <Bot size={18} />
                    </div>
                  )}
                  <div className={`max-w-[75%] p-3 rounded-2xl text-sm ${
                    msg.role === 'user'
                      ? 'bg-primary-600 text-white rounded-br-md'
                      : 'bg-gray-100 dark:bg-gray-800 text-gray-900 dark:text-white rounded-bl-md'
                  }`}>
                    {msg.content}
                  </div>
                  {msg.role === 'user' && (
                    <div className="w-8 h-8 rounded-xl bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-300 flex items-center justify-center flex-shrink-0">
                      <User size={18} />
                    </div>
                  )}
                </div>
              ))}
              {chatLoading && (
                <div className="flex gap-3">
                  <div className="w-8 h-8 rounded-xl bg-primary-100 dark:bg-primary-900/30 text-primary-600 dark:text-primary-300 flex items-center justify-center">
                    <Bot size={18} />
                  </div>
                  <div className="p-3 rounded-2xl bg-gray-100 dark:bg-gray-800">
                    <Loader2 size={18} className="animate-spin text-primary-600" />
                  </div>
                </div>
              )}
            </div>
            <form onSubmit={handleChatSubmit} className="flex gap-2">
              <input value={chatInput} onChange={(e) => setChatInput(e.target.value)} className="input-field flex-1" placeholder="Describe your HCP interaction..." disabled={chatLoading} />
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
