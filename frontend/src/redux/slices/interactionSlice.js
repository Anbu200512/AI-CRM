import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
import { interactionService } from '../../services/api'

export const fetchInteractions = createAsyncThunk('interactions/fetch', async (params, { rejectWithValue }) => {
  try {
    const res = await interactionService.getAll(params)
    return res.data
  } catch (err) {
    return rejectWithValue(err.response?.data?.detail || 'Failed to fetch')
  }
})

export const fetchInteraction = createAsyncThunk('interactions/fetchOne', async (id, { rejectWithValue }) => {
  try {
    const res = await interactionService.getById(id)
    return res.data
  } catch (err) {
    return rejectWithValue(err.response?.data?.detail || 'Not found')
  }
})

export const createInteraction = createAsyncThunk('interactions/create', async (data, { rejectWithValue }) => {
  try {
    const res = await interactionService.create(data)
    return res.data
  } catch (err) {
    return rejectWithValue(err.response?.data?.detail || 'Failed to create')
  }
})

export const updateInteraction = createAsyncThunk('interactions/update', async ({ id, data }, { rejectWithValue }) => {
  try {
    const res = await interactionService.update(id, data)
    return res.data
  } catch (err) {
    return rejectWithValue(err.response?.data?.detail || 'Failed to update')
  }
})

export const deleteInteraction = createAsyncThunk('interactions/delete', async (id, { rejectWithValue }) => {
  try {
    await interactionService.delete(id)
    return id
  } catch (err) {
    return rejectWithValue(err.response?.data?.detail || 'Failed to delete')
  }
})

const initialState = {
  items: [],
  total: 0,
  current: null,
  page: 1,
  pageSize: 10,
  loading: false,
  error: null,
}

const interactionSlice = createSlice({
  name: 'interactions',
  initialState,
  reducers: {
    setPage(state, action) { state.page = action.payload },
    clearCurrent(state) { state.current = null },
  },
  extraReducers: (builder) => {
    builder
      .addCase(fetchInteractions.pending, (state) => { state.loading = true })
      .addCase(fetchInteractions.fulfilled, (state, action) => {
        state.loading = false; state.items = action.payload.data; state.total = action.payload.total
      })
      .addCase(fetchInteractions.rejected, (state, action) => { state.loading = false; state.error = action.payload })
      .addCase(fetchInteraction.fulfilled, (state, action) => { state.current = action.payload })
      .addCase(createInteraction.fulfilled, (state, action) => { state.items.unshift(action.payload); state.total += 1 })
      .addCase(updateInteraction.fulfilled, (state, action) => {
        const idx = state.items.findIndex((i) => i.id === action.payload.id)
        if (idx >= 0) state.items[idx] = action.payload
        if (state.current?.id === action.payload.id) state.current = action.payload
      })
      .addCase(deleteInteraction.fulfilled, (state, action) => {
        state.items = state.items.filter((i) => i.id !== action.payload)
        state.total -= 1
      })
  },
})

export const { setPage, clearCurrent } = interactionSlice.actions
export default interactionSlice.reducer
