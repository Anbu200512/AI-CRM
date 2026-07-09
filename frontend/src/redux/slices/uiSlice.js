import { createSlice } from '@reduxjs/toolkit'

const initialState = {
  sidebarOpen: true,
  darkMode: localStorage.getItem('darkMode') === 'true',
  loading: false,
  notification: null,
}

const uiSlice = createSlice({
  name: 'ui',
  initialState,
  reducers: {
    toggleSidebar(state) { state.sidebarOpen = !state.sidebarOpen },
    setSidebarOpen(state, action) { state.sidebarOpen = action.payload },
    toggleDarkMode(state) {
      state.darkMode = !state.darkMode
      localStorage.setItem('darkMode', state.darkMode)
      if (state.darkMode) document.documentElement.classList.add('dark')
      else document.documentElement.classList.remove('dark')
    },
    setLoading(state, action) { state.loading = action.payload },
    setNotification(state, action) { state.notification = action.payload },
  },
})

export const { toggleSidebar, setSidebarOpen, toggleDarkMode, setLoading, setNotification } = uiSlice.actions
export default uiSlice.reducer
