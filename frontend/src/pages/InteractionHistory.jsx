import { useEffect, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { Link } from 'react-router-dom'
import { fetchInteractions, setPage } from '../redux/slices/interactionSlice'
import { interactionService } from '../services/api'
import Loader from '../components/ui/Loader'
import ErrorState from '../components/ui/ErrorState'
import EmptyState from '../components/ui/EmptyState'
import TableSkeleton from '../components/ui/TableSkeleton'
import { Search, Plus, ArrowUpDown, ChevronLeft, ChevronRight, Eye, Edit, Trash2, Calendar, Clock, User, Building2 } from 'lucide-react'
import { formatDate, capitalize } from '../utils'
import { motion } from 'framer-motion'

export default function InteractionHistory() {
  const dispatch = useDispatch()
  const { items, total, page, pageSize, loading, error } = useSelector((state) => state.interactions)
  const [search, setSearch] = useState('')
  const [sortBy, setSortBy] = useState('created_at')
  const [sortOrder, setSortOrder] = useState('desc')

  useEffect(() => {
    dispatch(fetchInteractions({ page, page_size: pageSize, search, sort_by: sortBy, sort_order: sortOrder }))
  }, [dispatch, page, pageSize, search, sortBy, sortOrder])

  const totalPages = Math.ceil(total / pageSize)

  const toggleSort = (field) => {
    if (sortBy === field) setSortOrder((prev) => (prev === 'asc' ? 'desc' : 'asc'))
    else { setSortBy(field); setSortOrder('desc') }
  }

  const handleDelete = async (id) => {
    if (!confirm('Delete this interaction?')) return
    try {
      await interactionService.delete(id)
      dispatch(fetchInteractions({ page, page_size: pageSize, search, sort_by: sortBy, sort_order: sortOrder }))
    } catch {
      alert('Failed to delete interaction')
    }
  }

  if (error) return <ErrorState message={error} onRetry={() => dispatch(fetchInteractions({ page, page_size: pageSize, search, sort_by: sortBy, sort_order: sortOrder }))} />

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Interaction History</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">{total} total interactions</p>
        </div>
        <Link to="/log-interaction" className="btn-primary flex items-center gap-2"><Plus size={18} />New Interaction</Link>
      </div>

      <div className="card p-4">
        <div className="flex flex-wrap items-center gap-3 mb-4">
          <div className="relative flex-1 min-w-[200px]">
            <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input className="input-field pl-10" placeholder="Search by doctor, summary, products..." value={search} onChange={(e) => { setSearch(e.target.value); dispatch(setPage(1)) }} />
          </div>
        </div>

        {loading ? <TableSkeleton rows={5} cols={6} /> : items.length === 0 ? (
          <EmptyState title="No interactions found" description="Start logging interactions with HCPs." action={<Link to="/log-interaction" className="btn-primary">Log Interaction</Link>} />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 dark:border-gray-700">
                  {[
                    { key: 'doctor_name', label: 'Doctor' },
                    { key: 'hospital', label: 'Hospital' },
                    { key: 'products', label: 'Products' },
                    { key: 'interest_level', label: 'Interest' },
                    { key: 'interaction_date', label: 'Date' },
                    { key: 'created_at', label: 'Created' },
                  ].map(({ key, label }) => (
                    <th key={key} className="text-left py-3 px-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">
                      <button onClick={() => toggleSort(key)} className="flex items-center gap-1 hover:text-gray-700 dark:hover:text-gray-300">
                        {label}
                        <ArrowUpDown size={12} />
                      </button>
                    </th>
                  ))}
                  <th className="text-right py-3 px-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Actions</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <motion.tr key={item.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
                    <td className="py-3 px-3">
                      <div className="flex items-center gap-2">
                        <User size={14} className="text-gray-400" />
                        <span className="font-medium text-gray-900 dark:text-white">{item.doctor_name || '—'}</span>
                      </div>
                    </td>
                    <td className="py-3 px-3">
                      <div className="flex items-center gap-2">
                        <Building2 size={14} className="text-gray-400" />
                        <span className="text-gray-600 dark:text-gray-400">{item.hospital || '—'}</span>
                      </div>
                    </td>
                    <td className="py-3 px-3 text-gray-600 dark:text-gray-400 max-w-[150px] truncate">{item.products || '—'}</td>
                    <td className="py-3 px-3">
                      <span className={`inline-flex text-xs font-medium px-2 py-0.5 rounded-lg ${
                        item.interest_level === 'High' ? 'bg-red-50 text-red-600 dark:bg-red-900/30 dark:text-red-300' :
                        item.interest_level === 'Medium' ? 'bg-amber-50 text-amber-600 dark:bg-amber-900/30 dark:text-amber-300' :
                        'bg-green-50 text-green-600 dark:bg-green-900/30 dark:text-green-300'
                      }`}>{item.interest_level || '—'}</span>
                    </td>
                    <td className="py-3 px-3">
                      <div className="flex items-center gap-2 text-gray-600 dark:text-gray-400">
                        <Calendar size={14} />
                        {item.interaction_date ? formatDate(item.interaction_date) : '—'}
                      </div>
                    </td>
                    <td className="py-3 px-3 text-gray-500 text-xs">{item.created_at ? formatDate(item.created_at) : '—'}</td>
                    <td className="py-3 px-3 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <Link to={`/interactions/${item.id}`} className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-400 hover:text-primary-600"><Eye size={16} /></Link>
                        <Link to={`/interactions/${item.id}/edit`} className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-400 hover:text-amber-600"><Edit size={16} /></Link>
                        <button onClick={() => handleDelete(item.id)} className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-400 hover:text-red-500" title="Delete"><Trash2 size={16} /></button>
                      </div>
                    </td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {totalPages > 1 && (
          <div className="flex items-center justify-between pt-4 border-t border-gray-200 dark:border-gray-700 mt-4">
            <p className="text-sm text-gray-500">Page {page} of {totalPages}</p>
            <div className="flex gap-1">
              <button disabled={page <= 1} onClick={() => dispatch(setPage(page - 1))} className="btn-secondary p-2 disabled:opacity-30"><ChevronLeft size={18} /></button>
              <button disabled={page >= totalPages} onClick={() => dispatch(setPage(page + 1))} className="btn-secondary p-2 disabled:opacity-30"><ChevronRight size={18} /></button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
