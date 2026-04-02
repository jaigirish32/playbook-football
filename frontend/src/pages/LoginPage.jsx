import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { login } from '../api/index'
import { useAuthStore, useThemeStore } from '../store/index'

export default function LoginPage() {
  const [email,    setEmail]    = useState('')
  const [password, setPassword] = useState('')
  const [error,    setError]    = useState('')
  const [loading,  setLoading]  = useState(false)
  const setAuth    = useAuthStore((s) => s.setAuth)
  const initTheme  = useThemeStore((s) => s.initTheme)
  const navigate   = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await login(email, password)
      setAuth(res.data.access_token, res.data.user)
      initTheme()
      navigate('/')
    } catch {
      setError('Invalid email or password')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      minHeight      : '100vh',
      background     : '#0d0d0d',
      display        : 'flex',
      alignItems     : 'center',
      justifyContent : 'center',
      fontFamily     : 'Barlow, sans-serif',
    }}>
      {/* Background texture */}
      <div style={{
        position  : 'fixed',
        inset     : 0,
        background: 'repeating-linear-gradient(45deg, #ffffff04 0, #ffffff04 1px, transparent 0, transparent 50%)',
        backgroundSize: '20px 20px',
        pointerEvents: 'none',
      }} />

      <div style={{
        background  : '#161616',
        border      : '1px solid #2a2a2a',
        borderTop   : '3px solid #e8b000',
        borderRadius: '8px',
        padding     : '48px 40px',
        width       : '100%',
        maxWidth    : '400px',
        position    : 'relative',
        boxShadow   : '0 24px 48px rgba(0,0,0,0.6)',
      }}>
        {/* Logo */}
        <div style={{ textAlign: 'center', marginBottom: '32px' }}>
          <div style={{
            fontFamily   : 'Oswald, sans-serif',
            fontSize     : '2rem',
            fontWeight   : '700',
            color        : '#e8b000',
            letterSpacing: '0.1em',
          }}>
            PLAYBOOK
          </div>
          <div style={{
            fontFamily   : 'Barlow Condensed, sans-serif',
            fontSize     : '0.9rem',
            color        : '#ffffff44',
            letterSpacing: '0.2em',
            textTransform: 'uppercase',
            marginTop    : '4px',
          }}>
            Football Intelligence
          </div>
        </div>

        <form onSubmit={handleSubmit}>
          {/* Email */}
          <div style={{ marginBottom: '16px' }}>
            <label style={{
              display     : 'block',
              fontFamily  : 'Barlow Condensed, sans-serif',
              fontSize    : '0.75rem',
              letterSpacing: '0.1em',
              textTransform: 'uppercase',
              color       : '#888',
              marginBottom: '6px',
            }}>
              Email
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              style={{
                width       : '100%',
                background  : '#0d0d0d',
                border      : '1px solid #2a2a2a',
                borderRadius: '4px',
                color       : '#f0ede8',
                fontFamily  : 'Barlow, sans-serif',
                fontSize    : '0.95rem',
                padding     : '10px 14px',
                outline     : 'none',
                transition  : 'border-color 0.15s',
              }}
              onFocus={(e) => e.target.style.borderColor = '#e8b000'}
              onBlur={(e)  => e.target.style.borderColor = '#2a2a2a'}
            />
          </div>

          {/* Password */}
          <div style={{ marginBottom: '24px' }}>
            <label style={{
              display     : 'block',
              fontFamily  : 'Barlow Condensed, sans-serif',
              fontSize    : '0.75rem',
              letterSpacing: '0.1em',
              textTransform: 'uppercase',
              color       : '#888',
              marginBottom: '6px',
            }}>
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              style={{
                width       : '100%',
                background  : '#0d0d0d',
                border      : '1px solid #2a2a2a',
                borderRadius: '4px',
                color       : '#f0ede8',
                fontFamily  : 'Barlow, sans-serif',
                fontSize    : '0.95rem',
                padding     : '10px 14px',
                outline     : 'none',
                transition  : 'border-color 0.15s',
              }}
              onFocus={(e) => e.target.style.borderColor = '#e8b000'}
              onBlur={(e)  => e.target.style.borderColor = '#2a2a2a'}
            />
          </div>

          {error && (
            <div style={{
              background  : '#2e0d0d',
              border      : '1px solid #c0392b',
              borderRadius: '4px',
              color       : '#ef5350',
              fontSize    : '0.85rem',
              padding     : '10px 14px',
              marginBottom: '16px',
              fontFamily  : 'Barlow Condensed, sans-serif',
            }}>
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            style={{
              width       : '100%',
              background  : loading ? '#9a7700' : '#e8b000',
              border      : 'none',
              borderRadius: '4px',
              color       : '#0d0d0d',
              cursor      : loading ? 'not-allowed' : 'pointer',
              fontFamily  : 'Oswald, sans-serif',
              fontSize    : '1rem',
              fontWeight  : '600',
              letterSpacing: '0.1em',
              padding     : '12px',
              textTransform: 'uppercase',
              transition  : 'background 0.15s',
            }}
          >
            {loading ? 'SIGNING IN...' : 'SIGN IN'}
          </button>
        </form>
      </div>
    </div>
  )
}
