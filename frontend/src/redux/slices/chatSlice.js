import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
import { chatService } from '../../services/api'

export const sendMessage = createAsyncThunk('chat/sendMessage', async (message, { getState, rejectWithValue }) => {
  try {
    const { conversationId } = getState().chat
    const res = await chatService.chat({ message, conversation_id: conversationId })
    return res.data
  } catch (err) {
    return rejectWithValue(err.response?.data?.detail || 'Failed to send message')
  }
})

export const extractEntities = createAsyncThunk('chat/extractEntities', async (text, { rejectWithValue }) => {
  try {
    const res = await chatService.extract({ text })
    return res.data
  } catch (err) {
    return rejectWithValue(err.response?.data?.detail || 'Extraction failed')
  }
})

const initialState = {
  messages: [],
  extracted: null,
  conversationId: null,
  loading: false,
  error: null,
}

const chatSlice = createSlice({
  name: 'chat',
  initialState,
  reducers: {
    addMessage(state, action) {
      state.messages.push(action.payload)
    },
    clearChat(state) {
      state.messages = []
      state.extracted = null
      state.conversationId = null
    },
    updateExtracted(state, action) {
      state.extracted = { ...state.extracted, ...action.payload }
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(sendMessage.pending, (state) => { state.loading = true; state.error = null })
      .addCase(sendMessage.fulfilled, (state, action) => {
        state.loading = false
        state.messages.push({ role: 'assistant', content: action.payload.response })
        state.extracted = action.payload.extracted
        state.conversationId = action.payload.conversation_id
      })
      .addCase(sendMessage.rejected, (state, action) => { state.loading = false; state.error = action.payload })
      .addCase(extractEntities.fulfilled, (state, action) => {
        state.extracted = action.payload
      })
  },
})

export const { addMessage, clearChat, updateExtracted } = chatSlice.actions
export default chatSlice.reducer
