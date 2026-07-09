import { useEffect } from 'react'
import { useSelector, useDispatch } from 'react-redux'
import { toggleDarkMode } from '../redux/slices/uiSlice'

export function useTheme() {
  const dispatch = useDispatch()
  const darkMode = useSelector((state) => state.ui.darkMode)

  useEffect(() => {
    if (darkMode) document.documentElement.classList.add('dark')
    else document.documentElement.classList.remove('dark')
  }, [darkMode])

  return { darkMode, toggle: () => dispatch(toggleDarkMode()) }
}
