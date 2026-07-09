import { configureStore } from '@reduxjs/toolkit'
import authReducer from './slices/authSlice'
import chatReducer from './slices/chatSlice'
import conversationsReducer from './slices/conversationsSlice'
import interactionReducer from './slices/interactionSlice'
import dashboardReducer from './slices/dashboardSlice'
import uiReducer from './slices/uiSlice'

export const store = configureStore({
  reducer: {
    auth: authReducer,
    chat: chatReducer,
    conversations: conversationsReducer,
    interactions: interactionReducer,
    dashboard: dashboardReducer,
    ui: uiReducer,
  },
})
