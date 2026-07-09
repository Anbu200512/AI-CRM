import { useEffect } from 'react'
import { useDispatch } from 'react-redux'
import AppRoutes from './routes/AppRoutes'
import { toggleDarkMode } from './redux/slices/uiSlice'

export default function App() {
  const dispatch = useDispatch()

  useEffect(() => {
    const isDark = localStorage.getItem('darkMode') === 'true'
    if (isDark) document.documentElement.classList.add('dark')
    else document.documentElement.classList.remove('dark')
  }, [])

  return <AppRoutes />
}
