import { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useThemeStore, useAuthStore } from './store/index'

import Layout     from './components/Layout'
import LoginPage  from './pages/LoginPage'
import HomePage   from './pages/HomePage'
import TeamPage   from './pages/TeamPage'
import ChatPage   from './pages/ChatPage'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 5 * 60 * 1000 },
  },
})

function PrivateRoute({ children }) {
  const token = useAuthStore((s) => s.token)
  return token ? children : <Navigate to="/login" replace />
}

export default function App() {
  const initTheme = useThemeStore((s) => s.initTheme)

  useEffect(() => { initTheme() }, [initTheme])

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/"
            element={
              <PrivateRoute>
                <Layout />
              </PrivateRoute>
            }
          >
            <Route index element={<HomePage />} />
            <Route path="team/:league/:abbr" element={<TeamPage />} />
            <Route path="chat"              element={<ChatPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
