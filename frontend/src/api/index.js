import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  headers: { 'Content-Type': 'application/json' },
})

// Attach JWT token to every request
api.interceptors.request.use((config) => {
  const raw = localStorage.getItem('playbook-auth')
  if (raw) {
    const { state } = JSON.parse(raw)
    if (state?.token) {
      config.headers.Authorization = `Bearer ${state.token}`
    }
  }
  return config
})

// Add after the request interceptor
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('playbook-auth')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// ── Auth ──────────────────────────────────────────────────────
export const login = (email, password) => {
  const form = new URLSearchParams()
  form.append('username', email)
  form.append('password', password)
  return api.post('/auth/login', form, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  })
}

// ── Teams ─────────────────────────────────────────────────────
export const fetchTeams     = (league = 'NFL', conference, division) =>
  api.get('/teams', { params: { league, conference, division } })

export const fetchTeam      = (id) => api.get(`/teams/${id}`)
export const fetchTeamByAbbr = (abbr, league = 'NFL') =>
  api.get(`/teams/abbr/${abbr}`, { params: { league } })

export const searchTeams    = (q, league = 'NFL') =>
  api.get('/teams/search', { params: { q, league } })

// ── Stats ─────────────────────────────────────────────────────
export const fetchSeasonStats = (teamId) => api.get(`/stats/season/${teamId}`)
export const fetchSOSStats    = (teamId) => api.get(`/stats/sos/${teamId}`)
export const fetchTrends      = (teamId, year) =>
  api.get(`/stats/trends/${teamId}/${year}`)

// ── Coaches ───────────────────────────────────────────────────
export const fetchCoach = (teamId) => api.get(`/coaches/${teamId}`)

// ── Chat ──────────────────────────────────────────────────────
export const askQuestion = (question) => api.post('/chat', { question })

export const fetchSchedule   = (teamId) => api.get(`/stats/schedule/${teamId}`)
export const fetchGameLogs   = (teamId) => api.get(`/stats/gamelogs/${teamId}`)
export const fetchDraftPicks = (teamId) => api.get(`/stats/draftpicks/${teamId}`)

export const fetchPlaybook = (teamId) => api.get(`/stats/playbook/${teamId}`)

export const fetchAtsHistory = (teamId, year) => api.get(`/stats/ats-history/${teamId}?season_year=${year}`)


