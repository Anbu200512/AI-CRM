import { useEffect, useRef, useState, useCallback } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { Link } from 'react-router-dom'
import { fetchDashboard } from '../redux/slices/dashboardSlice'
import { interactionService, getWsUrl } from '../services/api'
import StatCard from '../components/ui/StatCard'
import Loader from '../components/ui/Loader'
import ErrorState from '../components/ui/ErrorState'
import EmptyState from '../components/ui/EmptyState'
import { CalendarPlus, MessageSquareText, History, RefreshCw, TrendingUp, Trash2 } from 'lucide-react'
import { Users, Calendar, Clock } from 'lucide-react'
import { formatDate } from '../utils'
import { motion } from 'framer-motion'

export default function Dashboard() {
  const dispatch = useDispatch()
  const { stats, recentActivities, upcomingFollowups, weeklyData, loading, error } = useSelector((state) => state.dashboard)
  const [lastUpdated, setLastUpdated] = useState(null)
  const intervalRef = useRef(null)

  const refresh = useCallback(() => {
    dispatch(fetchDashboard()).then(() => setLastUpdated(new Date()))
  }, [dispatch])

  useEffect(() => {
    refresh()
    const token = localStorage.getItem('token')
    let ws = null
    
    if (token) {
      ws = new WebSocket(`${getWsUrl('/ws/dashboard')}?token=${token}`)
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          if (data.type === 'DASHBOARD_UPDATED') {
            refresh()
          }
        } catch (e) {
          console.error('Failed to parse WebSocket message', e)
        }
      }
      ws.onerror = (error) => console.error('WebSocket error:', error)
    }

    return () => {
      if (ws) ws.close()
    }
  }, [refresh])

  if (loading && !stats.total_hcps) return <Loader />
  if (error) return <ErrorState message={error} onRetry={refresh} />

  const statCards = [
    { icon: Users, label: 'Total HCPs', value: stats.total_hcps, color: 'primary', trend: stats.total_hcps_trend },
    { icon: Calendar, label: 'Interactions Today', value: stats.interactions_today, color: 'green', trend: stats.interactions_today_trend },
    { icon: Clock, label: 'Pending Follow-ups', value: stats.pending_followups, color: 'amber' },
    { icon: TrendingUp, label: 'Weekly Meetings', value: stats.weekly_meetings, color: 'purple', trend: stats.weekly_meetings_trend },
  ]

  const todayStr = new Date().toLocaleDateString('en-CA')
  const totalInteractions = weeklyData.reduce((sum, d) => sum + d.count, 0)
  const avgInteractions = weeklyData.length ? Math.round(totalInteractions / weeklyData.length) : 0
  const maxCount = weeklyData.length ? Math.max(...weeklyData.map(d => d.count)) : 0

  const handleDelete = async (id, e) => {
    e.preventDefault()
    e.stopPropagation()
    if (!confirm('Delete this interaction?')) return
    try {
      await interactionService.delete(id)
      refresh()
    } catch {
      alert('Failed to delete interaction')
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Dashboard</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">Overview of your HCP interactions</p>
        </div>
        <div className="flex items-center gap-3">
          {lastUpdated && (
            <span className="text-[11px] text-gray-400 hidden sm:block">
              Updated {lastUpdated.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}
            </span>
          )}
          <button onClick={refresh} className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors" title="Refresh">
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
          </button>
          <Link to="/log-interaction" className="btn-primary flex items-center gap-2"><CalendarPlus size={18} />Log Interaction</Link>
          <Link to="/chat" className="btn-secondary flex items-center gap-2"><MessageSquareText size={18} />AI Chat</Link>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map((card, i) => (
          <motion.div key={i} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.1 }}>
            <StatCard {...card} />
          </motion.div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 card p-5">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Weekly Activity</h3>
            {weeklyData.length > 0 && (
              <div className="flex items-center gap-4 text-xs text-gray-500 dark:text-gray-400">
                <span>Total: <strong className="text-gray-700 dark:text-gray-200">{totalInteractions}</strong></span>
                <span>Avg: <strong className="text-gray-700 dark:text-gray-200">{avgInteractions}</strong>/day</span>
              </div>
            )}
          </div>
          {weeklyData.length > 0 ? (
            <div className="flex items-end justify-between gap-2 px-2">
              {[...weeklyData].sort((a, b) => a.day.localeCompare(b.day)).map((entry) => {
                const isToday = entry.day === todayStr
                const intensity = maxCount > 0 ? entry.count / maxCount : 0
                const level = intensity === 0 ? 0 : intensity > 0.75 ? 4 : intensity > 0.5 ? 3 : intensity > 0.25 ? 2 : 1
                const colors = ['bg-gray-100 dark:bg-gray-800', 'bg-blue-200 dark:bg-blue-900', 'bg-blue-400 dark:bg-blue-700', 'bg-blue-600 dark:bg-blue-500', 'bg-blue-800 dark:bg-blue-400']
                return (
                  <div key={entry.day} className="flex flex-col items-center gap-1.5">
                    <span className="text-[10px] font-medium text-gray-400">{new Date(entry.day).toLocaleDateString('en-IN', { weekday: 'short' })}</span>
                    <div className={`w-10 h-10 sm:w-12 sm:h-12 rounded-lg ${colors[level]} ${isToday ? 'ring-2 ring-purple-500 ring-offset-2 dark:ring-offset-gray-950' : ''} flex items-center justify-center transition-all hover:scale-110`}>
                      <span className={`text-sm font-bold ${level > 2 ? 'text-white' : 'text-gray-600 dark:text-gray-300'}`}>{entry.count}</span>
                    </div>
                    <span className={`text-[10px] ${isToday ? 'text-purple-600 dark:text-purple-300 font-semibold' : 'text-gray-400'}`}>
                      {new Date(entry.day).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })}
                    </span>
                  </div>
                )
              })}
            </div>
          ) : (
            <EmptyState title="No weekly data" description="Start logging interactions to see your weekly activity." />
          )}
        </div>

        <div className="space-y-4">
          <div className="card p-5">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">Recent Activities</h3>
            {recentActivities.length > 0 ? (
              <div className="space-y-3">
                {recentActivities.map((activity) => (
                  <div key={activity.id} className="group flex items-center gap-3 p-2 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
                    <Link to={`/interactions/${activity.id}`} className="flex items-center gap-3 flex-1 min-w-0">
                      <div className="w-8 h-8 rounded-lg bg-primary-50 dark:bg-primary-900/30 text-primary-600 dark:text-primary-300 flex items-center justify-center">
                        <History size={16} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 dark:text-white truncate">{activity.doctor_name || 'Unknown Doctor'}</p>
                        <p className="text-xs text-gray-500">{activity.interaction_type?.replace(/_/g, ' ') || 'Interaction'}</p>
                      </div>
                    </Link>
                    <button onClick={(e) => handleDelete(activity.id, e)} className="p-1.5 rounded-lg text-gray-300 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 opacity-0 group-hover:opacity-100 transition-all" title="Delete">
                      <Trash2 size={14} />
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState title="No recent activity" />
            )}
          </div>

          <div className="card p-5">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">Upcoming Follow-ups</h3>
            {upcomingFollowups.length > 0 ? (
              <div className="space-y-3">
                {upcomingFollowups.map((fu) => (
                  <Link key={fu.id} to={`/interactions/${fu.id}`} className="flex items-center gap-3 p-2 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
                    <div className={`w-2 h-2 rounded-full ${fu.interest_level === 'High' ? 'bg-red-500' : fu.interest_level === 'Medium' ? 'bg-amber-500' : 'bg-green-500'}`} />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 dark:text-white truncate">{fu.doctor_name}</p>
                      <p className="text-xs text-gray-500">{formatDate(fu.follow_up_date)}</p>
                    </div>
                    <span className={`text-xs font-medium px-2 py-0.5 rounded-lg ${fu.interest_level === 'High' ? 'bg-red-50 text-red-600 dark:bg-red-900/30 dark:text-red-300' : fu.interest_level === 'Medium' ? 'bg-amber-50 text-amber-600' : 'bg-green-50 text-green-600'}`}>
                      {fu.interest_level}
                    </span>
                  </Link>
                ))}
              </div>
            ) : (
              <EmptyState title="No upcoming follow-ups" />
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
