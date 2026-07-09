import { useAuth } from '../hooks/useAuth'
import { useTheme } from '../hooks/useTheme'
import { User, Sun, Moon, LogOut, Shield, Bell } from 'lucide-react'
import { getInitials } from '../utils'

export default function Settings() {
  const { user, logout } = useAuth()
  const { darkMode, toggle } = useTheme()

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Settings</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400">Manage your account and preferences</p>
      </div>

      <div className="card p-6">
        <h3 className="font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
          <User size={18} className="text-primary-600" /> Profile
        </h3>
        <div className="flex items-center gap-4 mb-4">
          <div className="w-14 h-14 rounded-2xl bg-primary-100 dark:bg-primary-900/30 text-primary-600 dark:text-primary-300 flex items-center justify-center text-xl font-bold">
            {getInitials(user?.name)}
          </div>
          <div>
            <p className="font-semibold text-gray-900 dark:text-white">{user?.name}</p>
            <p className="text-sm text-gray-500">{user?.email}</p>
            <span className="inline-block mt-1 text-xs font-medium px-2 py-0.5 rounded-lg bg-primary-50 dark:bg-primary-900/30 text-primary-600 dark:text-primary-300 capitalize">{user?.role?.replace(/_/g, ' ')}</span>
          </div>
        </div>
      </div>

      <div className="card p-6">
        <h3 className="font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
          {darkMode ? <Moon size={18} className="text-primary-600" /> : <Sun size={18} className="text-primary-600" />} Appearance
        </h3>
        <div className="flex items-center justify-between">
          <div>
            <p className="font-medium text-gray-900 dark:text-white">Dark Mode</p>
            <p className="text-sm text-gray-500">Toggle between light and dark themes</p>
          </div>
          <button onClick={toggle} className={`relative w-12 h-6 rounded-full transition-colors ${darkMode ? 'bg-primary-600' : 'bg-gray-300'}`}>
            <span className={`absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform ${darkMode ? 'translate-x-6' : ''}`} />
          </button>
        </div>
      </div>

      <div className="card p-6">
        <h3 className="font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
          <Shield size={18} className="text-primary-600" /> Account
        </h3>
        <button onClick={logout} className="flex items-center gap-2 text-red-600 hover:text-red-700 font-medium text-sm">
          <LogOut size={18} /> Sign Out
        </button>
      </div>
    </div>
  )
}
