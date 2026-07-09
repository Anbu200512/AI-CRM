import React from 'react'
import ReactDOM from 'react-dom/client'
import { Provider } from 'react-redux'
import { BrowserRouter } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import App from './App'
import { store } from './redux/store'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <Provider store={store}>
      <BrowserRouter>
        <Toaster position="top-right" toastOptions={{ className: '!bg-white !text-gray-900 !shadow-lg !border !border-gray-200' }} />
        <App />
      </BrowserRouter>
    </Provider>
  </React.StrictMode>
)
