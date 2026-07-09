import { Outlet } from 'react-router-dom'
import { useSelector } from 'react-redux'
import Navbar from '../components/layout/Navbar'
import Sidebar from '../components/layout/Sidebar'

export default function MainLayout() {
  const sidebarOpen = useSelector((state) => state.ui.sidebarOpen)

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
      <Sidebar />
      <div className={`transition-all duration-300 ${sidebarOpen ? 'ml-64' : 'ml-20'}`}>
        <Navbar />
        <main className="p-6 pt-20">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
