import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { useThemeStore, useAuthStore } from '../store/index'

export default function Layout() {
  const { theme, toggleTheme } = useThemeStore()
  const { user, logout }       = useAuthStore()
  const navigate               = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-primary)' }}>
      {/* ── Navbar ── */}
      <nav style={{
        background    : 'var(--bg-header)',
        borderBottom  : '3px solid var(--border-accent)',
        padding       : '0 24px',
        display       : 'flex',
        alignItems    : 'center',
        gap           : '0',
        height        : '56px',
        position      : 'sticky',
        top           : 0,
        zIndex        : 100,
        boxShadow     : 'var(--shadow-md)',
      }}>
        {/* Logo */}
        <NavLink to="/" style={{ textDecoration: 'none', marginRight: '32px' }}>
          <span style={{
            fontFamily   : 'Oswald, sans-serif',
            fontSize     : '1.4rem',
            fontWeight   : '700',
            color        : 'var(--text-accent)',
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
          }}>
            PLAYBOOK
          </span>
          <span style={{
            fontFamily   : 'Barlow Condensed, sans-serif',
            fontSize     : '1rem',
            color        : '#ffffff88',
            marginLeft   : '6px',
            letterSpacing: '0.1em',
          }}>
            FOOTBALL
          </span>
        </NavLink>

        {/* Nav links */}
        {[
          { to: '/',     label: 'NFL' },
          { to: '/?league=CFB', label: 'CFB' },
          { to: '/chat', label: 'AI Chat' },
        ].map(({ to, label }) => (
          <NavLink
            key={label}
            to={to}
            style={({ isActive }) => ({
              fontFamily   : 'Oswald, sans-serif',
              fontSize     : '0.9rem',
              fontWeight   : '500',
              letterSpacing: '0.06em',
              textTransform: 'uppercase',
              textDecoration: 'none',
              color        : isActive ? 'var(--text-accent)' : '#ffffff99',
              padding      : '0 16px',
              height       : '56px',
              display      : 'flex',
              alignItems   : 'center',
              borderBottom : isActive ? '3px solid var(--border-accent)' : '3px solid transparent',
              marginBottom : isActive ? '-3px' : 0,
              transition   : 'color 0.15s, border-color 0.15s',
            })}
          >
            {label}
          </NavLink>
        ))}

        {/* Spacer */}
        <div style={{ flex: 1 }} />

        {/* Theme toggle */}
        <button
          onClick={toggleTheme}
          title="Toggle theme"
          style={{
            background  : 'none',
            border      : '1px solid #ffffff22',
            borderRadius: '20px',
            color       : '#ffffff99',
            cursor      : 'pointer',
            padding     : '4px 12px',
            fontSize    : '0.8rem',
            fontFamily  : 'Barlow Condensed, sans-serif',
            letterSpacing: '0.05em',
            transition  : 'border-color 0.15s, color 0.15s',
            marginRight : '12px',
          }}
        >
          {theme === 'dark' ? '☀ LIGHT' : '☾ DARK'}
        </button>

        {/* User */}
        {user && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span style={{
              color     : '#ffffff66',
              fontSize  : '0.8rem',
              fontFamily: 'Barlow Condensed, sans-serif',
            }}>
              {user.email}
            </span>
            <button
              onClick={handleLogout}
              style={{
                background  : 'none',
                border      : '1px solid #ffffff22',
                borderRadius: '4px',
                color       : '#ffffff66',
                cursor      : 'pointer',
                padding     : '4px 10px',
                fontSize    : '0.75rem',
                fontFamily  : 'Barlow Condensed, sans-serif',
                letterSpacing: '0.05em',
              }}
            >
              LOGOUT
            </button>
          </div>
        )}
      </nav>

      {/* ── Page content ── */}
      <main style={{ maxWidth: '1400px', margin: '0 auto', padding: '24px 16px' }}>
        <Outlet />
      </main>
    </div>
  )
}
