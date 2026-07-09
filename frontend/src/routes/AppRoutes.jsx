import { Routes, Route, Navigate } from 'react-router-dom'
import { useSelector } from 'react-redux'
import MainLayout from '../layouts/MainLayout'
import AuthLayout from '../layouts/AuthLayout'
import Login from '../pages/Login'
import Register from '../pages/Register'
import Dashboard from '../pages/Dashboard'
import LogInteraction from '../pages/LogInteraction'
import InteractionHistory from '../pages/InteractionHistory'
import InteractionDetails from '../pages/InteractionDetails'
import EditInteraction from '../pages/EditInteraction'
import ChatAssistant from '../pages/ChatAssistant'
import Settings from '../pages/Settings'
import NotFound from '../pages/NotFound'

function ProtectedRoute({ children }) {
  const isAuthenticated = useSelector((state) => state.auth.isAuthenticated)
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return children
}

function PublicRoute({ children }) {
  const isAuthenticated = useSelector((state) => state.auth.isAuthenticated)
  if (isAuthenticated) return <Navigate to="/" replace />
  return children
}

export default function AppRoutes() {
  return (
    <Routes>
      <Route element={<PublicRoute><AuthLayout /></PublicRoute>}>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
      </Route>
      <Route element={<ProtectedRoute><MainLayout /></ProtectedRoute>}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/log-interaction" element={<LogInteraction />} />
        <Route path="/history" element={<InteractionHistory />} />
        <Route path="/interactions/:id" element={<InteractionDetails />} />
        <Route path="/interactions/:id/edit" element={<EditInteraction />} />
        <Route path="/chat" element={<ChatAssistant />} />
        <Route path="/settings" element={<Settings />} />
      </Route>
      <Route path="*" element={<NotFound />} />
    </Routes>
  )
}
