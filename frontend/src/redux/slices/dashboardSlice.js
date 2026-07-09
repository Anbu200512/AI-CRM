import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
import { dashboardService } from '../../services/api'

export const fetchDashboard = createAsyncThunk('dashboard/fetch', async (_, { rejectWithValue }) => {
  try {
    const res = await dashboardService.get()
    return res.data
  } catch (err) {
    return rejectWithValue(err.response?.data?.detail || 'Failed to fetch dashboard')
  }
})

const initialState = {
  stats: { total_hcps: 0, interactions_today: 0, pending_followups: 0, weekly_meetings: 0 },
  recentActivities: [],
  upcomingFollowups: [],
  weeklyData: [],
  monthlyData: [],
  loading: false,
  error: null,
}

const dashboardSlice = createSlice({
  name: 'dashboard',
  initialState,
  reducers: {},
  extraReducers: (builder) => {
    builder
      .addCase(fetchDashboard.pending, (state) => { state.loading = true; state.error = null })
      .addCase(fetchDashboard.fulfilled, (state, action) => {
        state.loading = false
        state.stats = action.payload.stats
        state.recentActivities = action.payload.recent_activities
        state.upcomingFollowups = action.payload.upcoming_followups
        state.weeklyData = action.payload.weekly_data
        state.monthlyData = action.payload.monthly_data
      })
      .addCase(fetchDashboard.rejected, (state, action) => { state.loading = false; state.error = action.payload })
  },
})

export default dashboardSlice.reducer
