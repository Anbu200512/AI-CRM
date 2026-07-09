import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  headers: { 'Content-Type': 'application/json' },
})

export const getWsUrl = (path) => {
  const baseUrl = import.meta.env.VITE_API_URL || window.location.origin + '/api'
  const wsUrl = baseUrl.replace(/^http/, 'ws')
  return `${wsUrl}${path}`
}

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      console.error('[Auth] 401 received — clearing session', err.config?.url, err.response?.data)
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      window.location.href = '/login'
    } else if (err.response?.status >= 500) {
      console.error('[API] Server error', err.config?.url, err.response?.data)
    }
    return Promise.reject(err)
  }
)

export const authService = {
  login: (data) => api.post('/auth/login', data),
  register: (data) => api.post('/auth/register', data),
  profile: () => api.get('/auth/profile'),
}

export const interactionService = {
  getAll: (params) => api.get('/interactions', { params }),
  getById: (id) => api.get(`/interactions/${id}`),
  create: (data) => api.post('/interactions', data),
  update: (id, data) => api.put(`/interactions/${id}`, data),
  delete: (id) => api.delete(`/interactions/${id}`),
}

export const chatService = {
  chat: (data) => api.post('/ai/chat', data),
  extract: (data) => api.post('/ai/extract', data),
  summarize: (data) => api.post('/ai/summarize', data),
  followup: (data) => api.post('/ai/followup', data),
  edit: (data) => api.post('/ai/edit', data),
  entities: (data) => api.post('/ai/entities', data),
  sentiment: (data) => api.post('/ai/sentiment', data),
}

export const conversationService = {
  getAll: () => api.get('/conversations'),
  create: () => api.post('/conversations'),
  delete: (id) => api.delete(`/conversations/${id}`),
  getMessages: (id) => api.get(`/conversations/${id}/messages`),
  updateTitle: (id, title) => api.put(`/conversations/${id}/title`, { title }),
}

export const dashboardService = {
  get: () => api.get('/dashboard'),
}

export default api
