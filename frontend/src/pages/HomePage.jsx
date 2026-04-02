import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { fetchTeams } from '../api/index'

const NFL_DIVISIONS = [
  { conf: 'AFC', divs: ['AFC East', 'AFC North', 'AFC South', 'AFC West'] },
  { conf: 'NFC', divs: ['NFC East', 'NFC North', 'NFC South', 'NFC West'] },
]

const CFB_CONFERENCES = [
  'SEC', 'Big Ten', 'Big 12', 'ACC', 'Pac-12',
  'AAC', 'Mountain West', 'Sun Belt', 'Mid-American', 'CUSA', 'Independent',
]

export default function HomePage() {
  const [searchParams]           = useSearchParams()
  const league                   = searchParams.get('league') || 'NFL'
  const [search, setSearch]      = useState('')
  const [confFilter, setConfFilter] = useState('')
  const navigate                 = useNavigate()

  const { data: teams = [], isLoading } = useQuery({
    queryKey: ['teams', league],
    queryFn : () => fetchTeams(league).then((r) => r.data),
  })

  const filtered = teams.filter((t) => {
    const matchSearch = t.name.toLowerCase().includes(search.toLowerCase()) ||
                        t.abbreviation.toLowerCase().includes(search.toLowerCase())
    const matchConf   = !confFilter || t.conference === confFilter ||
                        t.division?.includes(confFilter)
    return matchSearch && matchConf
  })

  // Group NFL teams by division
  const getGrouped = () => {
    if (league !== 'NFL') return null
    const grouped = {}
    NFL_DIVISIONS.forEach(({ conf, divs }) => {
      divs.forEach((div) => {
        grouped[div] = filtered.filter((t) => t.division === div)
      })
    })
    return grouped
  }

  const grouped = getGrouped()

  const handleTeamClick = (team) => {
    navigate(`/team/${league}/${team.abbreviation}`)
  }

  return (
    <div className="fade-in">
      {/* ── Header ── */}
      <div style={{ marginBottom: '24px', display: 'flex', alignItems: 'center', gap: '16px', flexWrap: 'wrap' }}>
        <h1 style={{
          fontFamily   : 'Oswald, sans-serif',
          fontSize     : '1.8rem',
          fontWeight   : '700',
          letterSpacing: '0.05em',
          textTransform: 'uppercase',
          color        : 'var(--text-primary)',
        }}>
          {league} <span style={{ color: 'var(--text-accent)' }}>TEAMS</span>
        </h1>

        {/* League toggle */}
        <div style={{ display: 'flex', gap: '4px', marginLeft: 'auto' }}>
          {['NFL', 'CFB'].map((l) => (
            <button
              key={l}
              onClick={() => navigate(l === 'NFL' ? '/' : '/?league=CFB')}
              style={{
                background  : league === l ? 'var(--border-accent)' : 'var(--bg-card)',
                border      : `1px solid ${league === l ? 'var(--border-accent)' : 'var(--border)'}`,
                borderRadius: '4px',
                color       : league === l ? '#0d0d0d' : 'var(--text-secondary)',
                cursor      : 'pointer',
                fontFamily  : 'Oswald, sans-serif',
                fontSize    : '0.85rem',
                fontWeight  : '600',
                letterSpacing: '0.06em',
                padding     : '6px 16px',
                transition  : 'all 0.15s',
              }}
            >
              {l}
            </button>
          ))}
        </div>
      </div>

      {/* ── Filters ── */}
      <div style={{ display: 'flex', gap: '12px', marginBottom: '24px', flexWrap: 'wrap' }}>
        <input
          placeholder={`Search ${league} teams...`}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{
            background  : 'var(--bg-card)',
            border      : '1px solid var(--border)',
            borderRadius: '4px',
            color       : 'var(--text-primary)',
            fontFamily  : 'Barlow, sans-serif',
            fontSize    : '0.9rem',
            padding     : '8px 14px',
            outline     : 'none',
            width       : '240px',
            transition  : 'border-color 0.15s',
          }}
          onFocus={(e) => e.target.style.borderColor = 'var(--border-accent)'}
          onBlur={(e)  => e.target.style.borderColor = 'var(--border)'}
        />

        <select
          value={confFilter}
          onChange={(e) => setConfFilter(e.target.value)}
          style={{
            background  : 'var(--bg-card)',
            border      : '1px solid var(--border)',
            borderRadius: '4px',
            color       : 'var(--text-primary)',
            fontFamily  : 'Barlow Condensed, sans-serif',
            fontSize    : '0.9rem',
            padding     : '8px 14px',
            outline     : 'none',
            cursor      : 'pointer',
          }}
        >
          <option value="">All {league === 'NFL' ? 'Conferences' : 'Conferences'}</option>
          {league === 'NFL'
            ? ['AFC', 'NFC'].map((c) => <option key={c} value={c}>{c}</option>)
            : CFB_CONFERENCES.map((c) => <option key={c} value={c}>{c}</option>)
          }
        </select>
      </div>

      {/* ── Loading ── */}
      {isLoading && (
        <div style={{ textAlign: 'center', padding: '60px', color: 'var(--text-muted)' }}>
          <div className="animate-pulse" style={{
            fontFamily: 'Oswald, sans-serif',
            fontSize  : '1rem',
            letterSpacing: '0.1em',
          }}>
            LOADING TEAMS...
          </div>
        </div>
      )}

      {/* ── NFL: grouped by division ── */}
      {!isLoading && league === 'NFL' && grouped && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '20px' }}>
          {NFL_DIVISIONS.flatMap(({ divs }) => divs).map((div) => {
            const divTeams = grouped[div] || []
            if (divTeams.length === 0) return null
            return (
              <div key={div} className="card" style={{ overflow: 'hidden' }}>
                <div className="section-title">{div}</div>
                <div>
                  {divTeams.map((team) => (
                    <TeamRow key={team.id} team={team} onClick={() => handleTeamClick(team)} />
                  ))}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* ── CFB: flat grid ── */}
      {!isLoading && league === 'CFB' && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '8px' }}>
          {filtered.map((team) => (
            <CFBTeamCard key={team.id} team={team} onClick={() => handleTeamClick(team)} />
          ))}
        </div>
      )}

      {!isLoading && filtered.length === 0 && (
        <div style={{ textAlign: 'center', padding: '60px', color: 'var(--text-muted)' }}>
          No teams found
        </div>
      )}
    </div>
  )
}

function TeamRow({ team, onClick }) {
  return (
    <button
      onClick={onClick}
      style={{
        width      : '100%',
        background : 'none',
        border     : 'none',
        borderBottom: '1px solid var(--border)',
        cursor     : 'pointer',
        display    : 'flex',
        alignItems : 'center',
        gap        : '12px',
        padding    : '10px 14px',
        textAlign  : 'left',
        transition : 'background 0.1s',
      }}
      onMouseEnter={(e) => e.currentTarget.style.background = 'color-mix(in srgb, var(--border-accent) 8%, transparent)'}
      onMouseLeave={(e) => e.currentTarget.style.background = 'none'}
    >
      <span style={{
        fontFamily   : 'Oswald, sans-serif',
        fontSize     : '0.75rem',
        fontWeight   : '600',
        color        : 'var(--text-accent)',
        letterSpacing: '0.06em',
        width        : '36px',
        flexShrink   : 0,
      }}>
        {team.abbreviation}
      </span>
      <span style={{
        fontFamily: 'Barlow Condensed, sans-serif',
        fontSize  : '0.95rem',
        fontWeight: '500',
        color     : 'var(--text-primary)',
        flex      : 1,
      }}>
        {team.name}
      </span>
      <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>›</span>
    </button>
  )
}

function CFBTeamCard({ team, onClick }) {
  return (
    <button
      onClick={onClick}
      className="card"
      style={{
        background : 'var(--bg-card)',
        border     : '1px solid var(--border)',
        borderRadius: '6px',
        cursor     : 'pointer',
        padding    : '10px 12px',
        textAlign  : 'left',
        transition : 'border-color 0.15s, transform 0.1s',
        width      : '100%',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = 'var(--border-accent)'
        e.currentTarget.style.transform   = 'translateY(-1px)'
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = 'var(--border)'
        e.currentTarget.style.transform   = 'translateY(0)'
      }}
    >
      <div style={{
        fontFamily   : 'Oswald, sans-serif',
        fontSize     : '0.7rem',
        color        : 'var(--text-accent)',
        letterSpacing: '0.08em',
        marginBottom : '2px',
      }}>
        {team.abbreviation}
      </div>
      <div style={{
        fontFamily: 'Barlow Condensed, sans-serif',
        fontSize  : '0.9rem',
        fontWeight: '500',
        color     : 'var(--text-primary)',
        lineHeight : 1.2,
      }}>
        {team.name}
      </div>
      {team.conference && (
        <div style={{
          fontFamily: 'Barlow Condensed, sans-serif',
          fontSize  : '0.72rem',
          color     : 'var(--text-muted)',
          marginTop : '3px',
        }}>
          {team.conference}
        </div>
      )}
    </button>
  )
}
