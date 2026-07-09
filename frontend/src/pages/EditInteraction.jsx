import { useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useDispatch, useSelector } from 'react-redux'
import { useForm } from 'react-hook-form'
import { fetchInteraction, updateInteraction } from '../redux/slices/interactionSlice'
import toast from 'react-hot-toast'
import Loader from '../components/ui/Loader'
import ErrorState from '../components/ui/ErrorState'
import { ArrowLeft, Save } from 'lucide-react'
import { INTERACTION_TYPES, INTEREST_LEVELS } from '../constants'

export default function EditInteraction() {
  const { id } = useParams()
  const navigate = useNavigate()
  const dispatch = useDispatch()
  const { current: item, loading, error } = useSelector((state) => state.interactions)
  const { register, handleSubmit, formState: { errors }, reset } = useForm()

  useEffect(() => {
    dispatch(fetchInteraction(id))
  }, [dispatch, id])

  useEffect(() => {
    if (item) {
      reset({
        summary: item.summary || '',
        discussion: item.discussion || '',
        products: item.products || '',
        competitors: item.competitors || '',
        sentiment: item.sentiment || '',
        interest_level: item.interest_level || '',
        follow_up_date: item.follow_up_date || '',
        duration: item.duration || '',
      })
    }
  }, [item, reset])

  const onSubmit = async (data) => {
    try {
      await dispatch(updateInteraction({ id, data })).unwrap()
      toast.success('Interaction updated!')
      navigate(`/interactions/${id}`)
    } catch {
      toast.error('Failed to update')
    }
  }

  if (loading) return <Loader />
  if (error) return <ErrorState message={error} onRetry={() => dispatch(fetchInteraction(id))} />
  if (!item) return <ErrorState message="Interaction not found" />

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex items-center gap-4">
        <button onClick={() => navigate(-1)} className="p-2 rounded-xl hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500">
          <ArrowLeft size={20} />
        </button>
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Edit Interaction</h1>
          <p className="text-sm text-gray-500">Updating record for {item.doctor_name || 'Doctor'}</p>
        </div>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="card p-6 space-y-5">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Products Discussed</label>
            <input {...register('products')} className="input-field" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Competitors</label>
            <input {...register('competitors')} className="input-field" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Sentiment</label>
            <select {...register('sentiment')} className="input-field">
              {['Positive', 'Neutral', 'Negative'].map((s) => <option key={s} value={s.toLowerCase()}>{s}</option>)}
            </select>
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
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Duration (minutes)</label>
            <input type="number" {...register('duration')} className="input-field" />
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Discussion</label>
          <textarea {...register('discussion')} rows={4} className="input-field resize-none" />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Summary</label>
          <textarea {...register('summary')} rows={3} className="input-field resize-none" />
        </div>
        <div className="flex gap-3">
          <button type="submit" className="btn-primary flex items-center gap-2"><Save size={18} /> Save Changes</button>
          <button type="button" onClick={() => navigate(-1)} className="btn-secondary">Cancel</button>
        </div>
      </form>
    </div>
  )
}
