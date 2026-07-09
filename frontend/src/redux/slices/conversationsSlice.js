import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
import { conversationService, chatService } from '../../services/api'

export const fetchConversations = createAsyncThunk('conversations/fetchAll', async (_, { rejectWithValue }) => {
  try {
    const res = await conversationService.getAll()
    return res.data
  } catch (err) {
    return rejectWithValue(err.response?.data?.detail || 'Failed to fetch conversations')
  }
})

export const createConversation = createAsyncThunk('conversations/create', async (_, { rejectWithValue }) => {
  try {
    const res = await conversationService.create()
    return res.data
  } catch (err) {
    return rejectWithValue(err.response?.data?.detail || 'Failed to create conversation')
  }
})

export const deleteConversation = createAsyncThunk('conversations/delete', async (id, { rejectWithValue }) => {
  try {
    await conversationService.delete(id)
    return id
  } catch (err) {
    return rejectWithValue(err.response?.data?.detail || 'Failed to delete conversation')
  }
})

export const fetchMessages = createAsyncThunk('conversations/fetchMessages', async (conversationId, { rejectWithValue }) => {
  try {
    const res = await conversationService.getMessages(conversationId)
    return { conversationId, messages: res.data }
  } catch (err) {
    return rejectWithValue(err.response?.data?.detail || 'Failed to fetch messages')
  }
})

export const sendChatMessage = createAsyncThunk('conversations/sendMessage', async ({ message, conversationId }, { rejectWithValue }) => {
  try {
    const res = await chatService.chat({ message, conversation_id: conversationId })
    return res.data
  } catch (err) {
    return rejectWithValue(err.response?.data?.detail || 'Failed to send message')
  }
})

const initialState = {
  conversations: [],
  activeConversationId: null,
  messages: [],
  loading: false,
  sending: false,
  error: null,
}

const conversationsSlice = createSlice({
  name: 'conversations',
  initialState,
  reducers: {
    setActiveConversation(state, action) {
      state.activeConversationId = action.payload
    },
    clearActiveConversation(state) {
      state.activeConversationId = null
      state.messages = []
    },
    addMessageLocally(state, action) {
      state.messages.push(action.payload)
    },
    updateConversationTitle(state, action) {
      const { id, title } = action.payload
      const conv = state.conversations.find((c) => c.id === id)
      if (conv) conv.title = title
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchConversations.pending, (state) => { state.loading = true; state.error = null })
      .addCase(fetchConversations.fulfilled, (state, action) => {
        state.loading = false
        state.conversations = action.payload
      })
      .addCase(fetchConversations.rejected, (state, action) => { state.loading = false; state.error = action.payload })
      .addCase(createConversation.fulfilled, (state, action) => {
        state.conversations.unshift(action.payload)
        state.activeConversationId = action.payload.id
        state.messages = []
      })
      .addCase(deleteConversation.fulfilled, (state, action) => {
        state.conversations = state.conversations.filter((c) => c.id !== action.payload)
        if (state.activeConversationId === action.payload) {
          state.activeConversationId = null
          state.messages = []
        }
      })
      .addCase(fetchMessages.pending, (state) => { state.loading = true })
      .addCase(fetchMessages.fulfilled, (state, action) => {
        state.loading = false
        state.messages = action.payload.messages
        state.activeConversationId = action.payload.conversationId
      })
      .addCase(fetchMessages.rejected, (state, action) => { state.loading = false; state.error = action.payload })
      .addCase(sendChatMessage.pending, (state) => { state.sending = true; state.error = null })
      .addCase(sendChatMessage.fulfilled, (state, action) => {
        state.sending = false
        const { response, conversation_id, title, extracted } = action.payload
        const now = new Date().toISOString()
        const conv = state.conversations.find((c) => c.id === conversation_id)
        if (conv) {
          if (title) conv.title = title
          conv.last_message = response.slice(0, 100)
          conv.message_count = (conv.message_count || 0) + 1
          conv.updated_at = now
        } else {
          state.conversations.unshift({ id: conversation_id, title: title || 'New Chat', last_message: response.slice(0, 100), message_count: 1, updated_at: now, created_at: now })
        }
        state.messages.push({ role: 'assistant', content: response, id: Date.now() + 1, created_at: now })
        state.activeConversationId = conversation_id
        if (extracted) state._lastExtracted = extracted
      })
      .addCase(sendChatMessage.rejected, (state, action) => { state.sending = false; state.error = action.payload })
  },
})

export const { setActiveConversation, clearActiveConversation, addMessageLocally, updateConversationTitle } = conversationsSlice.actions
export default conversationsSlice.reducer
