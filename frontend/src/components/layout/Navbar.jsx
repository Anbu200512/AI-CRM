import { useSelector } from 'react-redux'
import { useAuth } from '../../hooks/useAuth'
import { useTheme } from '../../hooks/useTheme'
import { Sun, Moon, Bell, LogOut } from 'lucide-react'
import { getInitials } from '../../utils'

export default function Navbar() {
  const user = useSelector((state) => state.auth.user)
  const sidebarOpen = useSelector((state) => state.ui.sidebarOpen)
  const { logout } = useAuth()
  const { darkMode, toggle } = useTheme()

  return (
    <header className={`fixed top-0 right-0 z-20 bg-white/80 dark:bg-gray-900/80 backdrop-blur-xl border-b border-gray-200 dark:border-gray-800 px-6 py-3 flex items-center justify-between transition-all duration-300 ${sidebarOpen ? 'left-64' : 'left-20'}`}>
      <div>
        <h1 className="text-lg font-semibold text-gray-900 dark:text-white">Welcome back, {user?.name?.split(' ')[0] || 'User'}</h1>
        <p className="text-xs text-gray-500 dark:text-gray-400">{new Date().toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })}</p>
      </div>

      <div className="flex items-center gap-3">
        <button onClick={toggle} className="p-2 rounded-xl hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500 dark:text-gray-400 transition-colors">
          {darkMode ? <Sun size={18} /> : <Moon size={18} />}
        </button>
        <button className="p-2 rounded-xl hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500 dark:text-gray-400 transition-colors relative">
          <Bell size={18} />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 rounded-full"></span>
        </button>
        <div className="flex items-center gap-3 pl-3 border-l border-gray-200 dark:border-gray-700">
          <div className="w-8 h-8 rounded-xl bg-primary-100 dark:bg-primary-900 text-primary-600 dark:text-primary-300 flex items-center justify-center text-sm font-semibold">
            {getInitials(user?.name)}
          </div>
          <button onClick={logout} className="p-2 rounded-xl hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500 dark:text-gray-400 transition-colors" title="Logout">
            <LogOut size={18} />
          </button>
        </div>
      </div>
    </header>
  )
}
