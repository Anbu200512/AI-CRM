import { useSelector, useDispatch } from 'react-redux'
import { useNavigate } from 'react-router-dom'
import { login, register, logout } from '../redux/slices/authSlice'

export function useAuth() {
  const dispatch = useDispatch()
  const navigate = useNavigate()
  const { user, isAuthenticated, loading, error } = useSelector((state) => state.auth)

  const handleLogin = async (data) => {
    const result = await dispatch(login(data))
    if (result.meta.requestStatus === 'fulfilled') navigate('/')
    return result
  }

  const handleRegister = async (data) => {
    const result = await dispatch(register(data))
    if (result.meta.requestStatus === 'fulfilled') navigate('/')
    return result
  }

  const handleLogout = () => {
    dispatch(logout())
    navigate('/login')
  }

  return { user, isAuthenticated, loading, error, login: handleLogin, register: handleRegister, logout: handleLogout }
}
