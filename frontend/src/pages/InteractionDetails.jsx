import { useEffect } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { useDispatch, useSelector } from 'react-redux'
import { fetchInteraction, deleteInteraction } from '../redux/slices/interactionSlice'
import toast from 'react-hot-toast'
import Loader from '../components/ui/Loader'
import ErrorState from '../components/ui/ErrorState'
import { ArrowLeft, Edit, Trash2, Calendar, Clock, User, Building2, Syringe, FileText, Smile, Sparkles, AlertTriangle } from 'lucide-react'
import { formatDate, formatTime, capitalize } from '../utils'
import { useState } from 'react'

export default function InteractionDetails() {
  const { id } = useParams()
  const navigate = useNavigate()
  const dispatch = useDispatch()
  const { current: item, loading, error } = useSelector((state) => state.interactions)
  const [showDelete, setShowDelete] = useState(false)

  useEffect(() => {
    dispatch(fetchInteraction(id))
  }, [dispatch, id])

  const handleDelete = async () => {
    try {
      await dispatch(deleteInteraction(id)).unwrap()
      toast.success('Interaction deleted')
      navigate('/history')
    } catch {
      toast.error('Failed to delete')
    }
  }

  if (loading) return <Loader />
  if (error) return <ErrorState message={error} onRetry={() => dispatch(fetchInteraction(id))} />
  if (!item) return <ErrorState message="Interaction not found" />

  const details = [
    { label: 'Doctor', value: item.doctor_name, icon: User },
    { label: 'Hospital', value: item.hospital, icon: Building2 },
    { label: 'Products', value: item.products, icon: Syringe },
    { label: 'Competitors', value: item.competitors || 'None', icon: FileText },
    { label: 'Interest Level', value: item.interest_level, icon: Sparkles },
    { label: 'Sentiment', value: item.sentiment, icon: Smile },
    { label: 'Date', value: formatDate(item.interaction_date), icon: Calendar },
    { label: 'Duration', value: formatTime(item.duration), icon: Clock },
    { label: 'Follow-up', value: formatDate(item.follow_up_date) || 'Not set', icon: Calendar },
    { label: 'Type', value: capitalize(item.interaction_type), icon: FileText },
  ]

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <Link to="/history" className="flex items-center gap-2 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 transition-colors">
          <ArrowLeft size={18} /> Back to History
        </Link>
        <div className="flex gap-2">
          <Link to={`/interactions/${id}/edit`} className="btn-secondary flex items-center gap-2"><Edit size={18} />Edit</Link>
          <button onClick={() => setShowDelete(true)} className="btn-danger flex items-center gap-2"><Trash2 size={18} />Delete</button>
        </div>
      </div>

      <div className="card p-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">Interaction Details</h1>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {details.map(({ label, value, icon: Icon }) => (
            <div key={label} className="p-3 rounded-xl bg-gray-50 dark:bg-gray-800">
              <div className="flex items-center gap-1.5 text-xs text-gray-500 mb-1">
                <Icon size={12} /> {label}
              </div>
              <p className="text-sm font-medium text-gray-900 dark:text-white capitalize">{value || '—'}</p>
            </div>
          ))}
        </div>
      </div>

      {item.discussion && (
        <div className="card p-6">
          <h3 className="font-semibold text-gray-900 dark:text-white mb-3">Discussion Notes</h3>
          <p className="text-sm text-gray-600 dark:text-gray-400 whitespace-pre-wrap">{item.discussion}</p>
        </div>
      )}

      {item.summary && (
        <div className="card p-6">
          <h3 className="font-semibold text-gray-900 dark:text-white mb-3">Summary</h3>
          <p className="text-sm text-gray-600 dark:text-gray-400">{item.summary}</p>
        </div>
      )}

      {showDelete && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-white dark:bg-gray-900 rounded-2xl p-6 max-w-sm w-full shadow-xl">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 rounded-xl bg-red-50 dark:bg-red-900/30 text-red-600">
                <AlertTriangle size={24} />
              </div>
              <div>
                <h3 className="font-semibold text-gray-900 dark:text-white">Delete Interaction</h3>
                <p className="text-sm text-gray-500">This action cannot be undone.</p>
              </div>
            </div>
            <div className="flex gap-2 justify-end">
              <button onClick={() => setShowDelete(false)} className="btn-secondary">Cancel</button>
              <button onClick={handleDelete} className="btn-danger">Delete</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
