import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { fetchTeamByAbbr, fetchSeasonStats, fetchSOSStats, fetchTrends, fetchCoach, fetchSchedule, fetchGameLogs, fetchDraftPicks, fetchPlaybook, fetchAtsHistory } from '../api/index'

export default function TeamPage() {
  const { league, abbr } = useParams()
  const navigate         = useNavigate()

  const { data: team, isLoading: teamLoading } = useQuery({
    queryKey: ['team', league, abbr],
    queryFn : () => fetchTeamByAbbr(abbr, league).then((r) => r.data),
  })

  const { data: stats = [] } = useQuery({
    queryKey: ['stats', team?.id],
    queryFn : () => fetchSeasonStats(team.id).then((r) => r.data),
    enabled : !!team?.id,
  })

  const { data: sos = [] } = useQuery({
    queryKey: ['sos', team?.id],
    queryFn : () => fetchSOSStats(team.id).then((r) => r.data),
    enabled : !!team?.id && league === 'NFL',
  })

  const { data: trends } = useQuery({
    queryKey: ['trends', team?.id, 2024],
    queryFn : () => fetchTrends(team.id, 2024).then((r) => r.data),
    enabled : !!team?.id,
  })

  const { data: coach } = useQuery({
    queryKey: ['coach', team?.id],
    queryFn : () => fetchCoach(team.id).then((r) => r.data),
    enabled : !!team?.id,
  })

  const { data: schedule = [] } = useQuery({
    queryKey: ['schedule', team?.id],
    queryFn : () => fetchSchedule(team.id).then((r) => r.data),
    enabled : !!team?.id,
  })

  const { data: gamelogs = [] } = useQuery({
    queryKey: ['gamelogs', team?.id],
    queryFn : () => fetchGameLogs(team.id).then((r) => r.data),
    enabled : !!team?.id,
  })

  const { data: draftpicks = [] } = useQuery({
    queryKey: ['draftpicks', team?.id],
    queryFn : () => fetchDraftPicks(team.id).then((r) => r.data),
    enabled : !!team?.id && league === 'NFL',
  })

  const [atsYear, setAtsYear] = useState(2024)

  const { data: atsHistory = [] } = useQuery({
    queryKey: ['atsHistory', team?.id, atsYear],
    queryFn : () => fetchAtsHistory(team.id, atsYear).then((r) => r.data),
    enabled : !!team?.id && (league === 'NFL' || league === 'CFB'),
  })

  const { data: playbook } = useQuery({
    queryKey: ['playbook', team?.id],
    queryFn : () => fetchPlaybook(team.id).then((r) => r.data?.[0]),
    enabled : !!team?.id,
  })

  if (teamLoading) return (
    <div style={{ textAlign: 'center', padding: '80px', color: 'var(--text-muted)' }}>
      <div style={{ fontFamily: 'Oswald, sans-serif', letterSpacing: '0.1em' }}>LOADING...</div>
    </div>
  )

  if (!team) return (
    <div style={{ textAlign: 'center', padding: '80px', color: 'var(--text-muted)' }}>Team not found</div>
  )

  const sortedStats = [...stats].sort((a, b) => a.season_year - b.season_year)

  return (
    <div className="fade-in">
      <button
        onClick={() => navigate(league === 'NFL' ? '/' : '/?league=CFB')}
        style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontFamily: 'Barlow Condensed, sans-serif', fontSize: '0.85rem', letterSpacing: '0.06em', marginBottom: '16px', padding: '0', display: 'flex', alignItems: 'center', gap: '6px' }}
      >
        ‹ BACK TO {league} TEAMS
      </button>

      <TeamHeader team={team} coach={coach} league={league} />

      {/* ── Main grid ── */}
      <div style={{ display: 'grid', gridTemplateColumns: league === 'NFL' ? '1fr 320px' : '1fr', gap: '20px', marginTop: '20px' }}>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>

          <div className="card" style={{ overflow: 'hidden' }}>
            <div className="section-title">4 YEAR STATISTICAL REVIEW</div>
            <StatsTable stats={sortedStats} league={league} />
          </div>

          {league === 'NFL' && sos.length > 0 && (
            <div className="card" style={{ overflow: 'hidden' }}>
              <div className="section-title">2025 STRENGTH OF SCHEDULE</div>
              <SOSTable sos={sos} />
            </div>
          )}

          {schedule.length > 0 && (
            <div className="card" style={{ overflow: 'hidden' }}>
              <div className="section-title">2025 SCHEDULE LOG</div>
              <ScheduleTable schedule={schedule} league={league} />
            </div>
          )}

          {gamelogs.length > 0 && (
            <div className="card" style={{ overflow: 'hidden' }}>
              <div className="section-title">2024 STAT LOGS</div>
              <GameLogsTable gamelogs={gamelogs} />
            </div>
          )}

          {league === 'NFL' && draftpicks.length > 0 && (
            <div className="card" style={{ overflow: 'hidden' }}>
              <div className="section-title">2025 DRAFT PICKS</div>
              <DraftPicksTable picks={draftpicks} />
            </div>
          )}

        </div>

        {/* NFL right column */}
        {league === 'NFL' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {trends && <TrendsPanel trends={trends} league={league} />}
            {playbook && (playbook.draft_grades || playbook.first_round || playbook.steal_of_draft) && (
              <div className="card" style={{ overflow: 'hidden' }}>
                <div className="section-title">2025 DRAFT ANALYSIS</div>
                {playbook.draft_grades && (
                  <div style={{ margin: '0 12px 10px', padding: '10px 12px', background: '#0a0a1a', borderRadius: '4px', border: '1px solid #3949ab44' }}>
                    <div style={{ fontFamily: 'Oswald', fontSize: '0.72rem', fontWeight: 700, color: '#7986cb', letterSpacing: '0.08em', marginBottom: '6px' }}>DRAFT GRADES</div>
                    <div style={{ fontFamily: 'Barlow Condensed', fontSize: '0.82rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>{playbook.draft_grades}</div>
                  </div>
                )}
                {playbook.first_round && (
                  <div style={{ margin: '0 12px 10px', padding: '10px 12px', background: 'var(--bg-table-alt)', borderRadius: '4px', borderLeft: '3px solid #7986cb' }}>
                    <div style={{ fontFamily: 'Oswald', fontSize: '0.72rem', fontWeight: 700, color: '#7986cb', letterSpacing: '0.08em', marginBottom: '6px' }}>FIRST ROUND</div>
                    <div style={{ fontFamily: 'Barlow', fontSize: '0.82rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>{playbook.first_round}</div>
                  </div>
                )}
                {playbook.steal_of_draft && (
                  <div style={{ margin: '0 12px 12px', padding: '10px 12px', background: 'var(--bg-table-alt)', borderRadius: '4px', borderLeft: '3px solid var(--text-accent)' }}>
                    <div style={{ fontFamily: 'Oswald', fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-accent)', letterSpacing: '0.08em', marginBottom: '6px' }}>STEAL OF THE DRAFT</div>
                    <div style={{ fontFamily: 'Barlow', fontSize: '0.82rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>{playbook.steal_of_draft}</div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* ── NFL Playbook full width ── */}
      {league === 'NFL' && playbook && (
        <div style={{ marginTop: '20px' }}>
          <NFLPlaybookPanel playbook={playbook} />
        </div>
      )}

      {/* ── CFB Playbook + Trends full width ── */}
      {league === 'CFB' && (playbook || trends) && (
        <div style={{ marginTop: '20px', display: 'grid', gridTemplateColumns: '1fr 320px', gap: '20px' }}>
          <div>
            {playbook && <CFBPlaybookPanel playbook={playbook} />}
          </div>
          <div>
            {trends && <TrendsPanel trends={trends} league={league} />}
          </div>
        </div>
      )}

      {/* ── 10 Year ATS History full width ── */}
      {(league === 'NFL' || league === 'CFB') && (
        <div className="card" style={{ overflow: 'hidden', marginTop: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 16px 0' }}>
            <div className="section-title" style={{ margin: 0, padding: 0, border: 'none' }}>10 YEAR ATS HISTORY</div>
            <select
              value={atsYear}
              onChange={(e) => setAtsYear(Number(e.target.value))}
              style={{ background: 'var(--bg-table-alt)', border: '1px solid var(--border)', color: 'var(--text-accent)', fontFamily: 'Oswald, sans-serif', fontSize: '0.85rem', padding: '4px 8px', borderRadius: '4px', cursor: 'pointer' }}
            >
              {[2024,2023,2022,2021,2020,2019,2018,2017,2016,2015].map(y => (
                <option key={y} value={y}>{y}</option>
              ))}
            </select>
          </div>
          <ATSHistoryTable history={atsHistory} league={league} />
        </div>
      )}
    </div>
  )
}

/* ── Team Header ───────────────────────────────────────────── */
function TeamHeader({ team, coach, league }) {
  return (
    <div style={{ background: 'var(--bg-header)', borderRadius: 'var(--radius-md)', padding: '20px 24px', display: 'flex', alignItems: 'center', gap: '24px', flexWrap: 'wrap', borderBottom: '3px solid var(--border-accent)' }}>
      <div style={{ width: '90px', height: '90px', flexShrink: 0 }}>
        <img
          src={league === 'NFL'
            ? `https://a.espncdn.com/i/teamlogos/nfl/500/${team.abbreviation.toLowerCase()}.png`
            : `https://a.espncdn.com/i/teamlogos/ncaa/500/scoreboard/${team.abbreviation.toLowerCase()}.png`
          }
          alt={team.name}
          style={{ width: '100%', height: '100%', objectFit: 'contain' }}
          onError={(e) => { e.target.style.display = 'none' }}
        />
      </div>
      <div style={{ flex: 1, minWidth: '200px' }}>
        <div style={{ fontFamily: 'Oswald, sans-serif', fontSize: '2.5rem', fontWeight: '700', color: 'var(--text-accent)', letterSpacing: '0.05em', lineHeight: 1 }}>{team.abbreviation}</div>
        <div style={{ fontFamily: 'Barlow Condensed, sans-serif', fontSize: '1.1rem', color: '#ffffff99', letterSpacing: '0.08em', marginTop: '4px' }}>{team.name}</div>
        {team.conference && (
          <div style={{ fontFamily: 'Barlow Condensed, sans-serif', fontSize: '0.8rem', color: '#ffffff44', letterSpacing: '0.1em', textTransform: 'uppercase', marginTop: '6px' }}>
            {team.conference} • {team.division}
          </div>
        )}
        {team.stadium && (
          <div style={{ fontFamily: 'Barlow Condensed, sans-serif', fontSize: '0.8rem', color: '#ffffff44', marginTop: '4px' }}>
            {team.stadium} {team.stadium_city && `• ${team.stadium_city}`}
          </div>
        )}
      </div>
      {coach && (
        <div style={{ background: '#ffffff08', border: '1px solid #ffffff11', borderRadius: '6px', padding: '12px 16px', minWidth: '200px' }}>
          <div style={{ fontFamily: 'Barlow Condensed, sans-serif', fontSize: '0.7rem', color: '#ffffff44', letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: '4px' }}>Head Coach</div>
          <div style={{ fontFamily: 'Oswald, sans-serif', fontSize: '1rem', fontWeight: '600', color: '#fff' }}>{coach.name}</div>
          {coach.years_with_team && <div style={{ fontFamily: 'Barlow Condensed, sans-serif', fontSize: '0.8rem', color: '#ffffff66', marginTop: '2px' }}>Year {coach.years_with_team}</div>}
          {coach.record_su_wins != null && (
            <div style={{ marginTop: '6px' }}>
              {league === 'NFL' && (
                <div style={{ fontFamily: 'Barlow Condensed, sans-serif', fontSize: '0.7rem', color: '#ffffff66', letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: '2px' }}>
                  Record With {team.name.split(' ').pop()}:
                </div>
              )}
              <div style={{ fontFamily: 'Barlow Condensed, sans-serif', fontSize: '0.85rem' }}>
              <span style={{ color: 'var(--text-accent)' }}>{coach.record_su_wins}-{coach.record_su_losses} SU</span>
              {coach.record_ats_wins != null && (
                <span style={{ color: 'var(--text-accent)', marginLeft: '8px' }}>
                  {coach.record_ats_wins}-{coach.record_ats_losses}{coach.record_ats_pushes > 0 ? `-${coach.record_ats_pushes}` : ''} ATS
                </span>
              )}</div>
            </div>
          )}
          {league === 'CFB' && (
            <div style={{ marginTop: '8px', display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
              {coach.rpr != null && (
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontFamily: 'Barlow Condensed', fontSize: '0.62rem', color: '#ffffff44', textTransform: 'uppercase', letterSpacing: '0.06em' }}>RPR</div>
                  <div style={{ fontFamily: 'Oswald', fontSize: '1rem', color: 'var(--text-accent)', fontWeight: 700 }}>{coach.rpr}</div>
                  {coach.rpr_off != null && (
                    <div style={{ fontFamily: 'Barlow Condensed', fontSize: '0.65rem', color: '#ffffff44' }}>Off:{coach.rpr_off} • Def:{coach.rpr_def}</div>
                  )}
                </div>
              )}
              {coach.ret_off_starters != null && (
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontFamily: 'Barlow Condensed', fontSize: '0.62rem', color: '#ffffff44', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Ret. Starters</div>
                  <div style={{ fontFamily: 'Oswald', fontSize: '1rem', fontWeight: 700 }}>
                    <span style={{ color: 'var(--text-win)' }}>{coach.ret_off_starters}</span>
                    <span style={{ color: '#ffffff44', margin: '0 3px' }}>OFF</span>
                    <span style={{ color: 'var(--text-secondary)' }}>{coach.ret_def_starters}</span>
                    <span style={{ color: '#ffffff44', margin: '0 3px' }}>DEF</span>
                  </div>
                </div>
              )}
              {coach.recruit_rank_2025 != null && (
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontFamily: 'Barlow Condensed', fontSize: '0.62rem', color: '#ffffff44', textTransform: 'uppercase', letterSpacing: '0.06em' }}>2025 Recruit Rank</div>
                  <div style={{ fontFamily: 'Oswald', fontSize: '1rem', color: '#FFD700', fontWeight: 700 }}>#{coach.recruit_rank_2025}</div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

/* ── Stats Table ───────────────────────────────────────────── */
function StatsTable({ stats, league }) {
  if (!stats.length) return <div style={{ padding: '24px', textAlign: 'center', color: 'var(--text-muted)' }}>No stats available</div>

  const fmtRec = (w, l, p) => { if (!w && !l) return '–'; return p ? `${w}-${l}-${p}` : `${w}-${l}` }
  const fmtNum = (n) => n != null ? n : '–'

  return (
    <div style={{ overflowX: 'auto' }}>
      <table className="stat-table">
        <thead>
          <tr>
            <th>YEAR</th>
            {league === 'CFB' && <th title="Returning Offensive Starters">O</th>}
            {league === 'CFB' && <th title="Returning Defensive Starters">D</th>}
            <th>SU</th><th>ATS</th>
            {league === 'NFL' && <th>DIV SU</th>}
            {league === 'NFL' && <th>DIV ATS</th>}
            {league === 'CFB' && <th>CONF SU</th>}
            {league === 'CFB' && <th>CONF ATS</th>}
            <th>HF</th><th>HD</th><th>RD</th><th>RF</th>
            <th>PF</th><th>PA</th>
            <th>YPR</th><th>RSH</th><th>PSS</th>
            <th>OFF TOT</th><th>DEF TOT</th><th>DEF PSS</th><th>DEF RSH</th><th>DEF YPR</th>
            {league === 'CFB' && <th title="Recruiting Rank">RK</th>}
            {league === 'CFB' && <th title="5-Star Recruits">5★</th>}
            {league === 'CFB' && <th title="4-Star Recruits">4★</th>}
            {league === 'CFB' && <th title="3-Star Recruits">3★</th>}
            {league === 'CFB' && <th title="Total Recruits">TOT</th>}
          </tr>
        </thead>
        <tbody>
          {stats.map((s) => (
            <tr key={s.id}>
              <td style={{ fontFamily: 'Oswald, sans-serif', color: 'var(--text-accent)', fontWeight: '600' }}>{s.season_year}</td>
              {league === 'CFB' && <td style={{ color: 'var(--text-win)', fontWeight: '600' }}>{fmtNum(s.ret_off_starters)}</td>}
              {league === 'CFB' && <td style={{ color: 'var(--text-secondary)' }}>{fmtNum(s.ret_def_starters)}</td>}
              <td><RecordCell w={s.su_wins} l={s.su_losses} /></td>
              <td><RecordCell w={s.ats_wins} l={s.ats_losses} p={s.ats_pushes} /></td>
              <td><RecordCell w={s.div_su_wins} l={s.div_su_losses} /></td>
              <td><RecordCell w={s.div_ats_wins} l={s.div_ats_losses} /></td>
              <td style={{ fontSize: '0.78rem' }}>{fmtRec(s.home_fav_ats_w, s.home_fav_ats_l)}</td>
              <td style={{ fontSize: '0.78rem' }}>{fmtRec(s.home_dog_ats_w, s.home_dog_ats_l)}</td>
              <td style={{ fontSize: '0.78rem' }}>{fmtRec(s.road_dog_ats_w, s.road_dog_ats_l)}</td>
              <td style={{ fontSize: '0.78rem' }}>{fmtRec(s.road_fav_ats_w, s.road_fav_ats_l)}</td>
              <td style={{ color: 'var(--text-win)', fontWeight: '600' }}>{fmtNum(s.points_for_avg)}</td>
              <td style={{ color: 'var(--text-loss)', fontWeight: '600' }}>{fmtNum(s.points_against_avg)}</td>
              <td>{fmtNum(s.off_ypr)}</td>
              <td>{fmtNum(s.off_rush_avg)}</td>
              <td>{fmtNum(s.off_pass_avg)}</td>
              <td style={{ fontWeight: '600' }}>{fmtNum(s.off_total_avg)}</td>
              <td style={{ fontWeight: '600' }}>{fmtNum(s.def_total_avg)}</td>
              <td>{fmtNum(s.def_pass_avg)}</td>
              <td>{fmtNum(s.def_rush_avg)}</td>
              <td>{fmtNum(s.def_ypr)}</td>
              {league === 'CFB' && <td style={{ color: 'var(--text-muted)', fontSize: '0.78rem' }}>{fmtNum(s.recruit_rank)}</td>}
              {league === 'CFB' && <td style={{ color: '#FFD700', fontWeight: '600' }}>{fmtNum(s.recruit_5star)}</td>}
              {league === 'CFB' && <td style={{ color: 'var(--text-accent)' }}>{fmtNum(s.recruit_4star)}</td>}
              {league === 'CFB' && <td style={{ color: 'var(--text-secondary)' }}>{fmtNum(s.recruit_3star)}</td>}
              {league === 'CFB' && <td style={{ color: 'var(--text-muted)' }}>{fmtNum(s.recruit_total)}</td>}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function RecordCell({ w, l, p }) {
  if (!w && !l) return <span style={{ color: 'var(--text-muted)' }}>–</span>
  return (
    <span>
      <span className="win">{w}</span>
      <span style={{ color: 'var(--text-muted)' }}>-</span>
      <span className="loss">{l}</span>
      {p > 0 && <span className="push">-{p}</span>}
    </span>
  )
}

/* ── SOS Table ─────────────────────────────────────────────── */
function SOSTable({ sos }) {
  const s = sos[0]
  if (!s) return null
  return (
    <div style={{ padding: '16px 14px' }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: '12px' }}>
        {[
          { label: 'SOS Rank',    value: s.sos_rank ? `#${s.sos_rank}` : '–' },
          { label: 'Win Total',   value: s.team_win_total ?? '–' },
          { label: 'Opp Win Pct', value: s.opp_win_pct ? `${(s.opp_win_pct * 100).toFixed(1)}%` : '–' },
          { label: 'vs Div Wins', value: s.vs_div_wins ?? '–' },
          { label: 'vs NonDiv',   value: s.vs_nondiv_wins ?? '–' },
        ].map(({ label, value }) => (
          <div key={label} style={{ background: 'var(--bg-table-alt)', border: '1px solid var(--border)', borderRadius: '4px', padding: '10px 12px', textAlign: 'center' }}>
            <div style={{ fontFamily: 'Barlow Condensed, sans-serif', fontSize: '0.7rem', color: 'var(--text-muted)', letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: '4px' }}>{label}</div>
            <div style={{ fontFamily: 'Oswald, sans-serif', fontSize: '1.2rem', fontWeight: '600', color: 'var(--text-accent)' }}>{value}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

/* ── Schedule Table ────────────────────────────────────────── */
function ScheduleTable({ schedule, league }) {
  const fmtSpread = (v) => v != null ? (v > 0 ? `+${v}` : v === 0 ? 'PK' : v) : '–'
  return (
    <div style={{ overflowX: 'auto' }}>
      <table className="stat-table">
        <thead>
          <tr>
            <th>DATE</th>
            <th style={{ textAlign: 'left' }}>OPPONENT</th>
            <th>OWL</th>
            {league === 'NFL' && <th>ADV</th>}
            <th>PF</th><th>PA</th>
            {league === 'NFL' && <th>LINE</th>}
            <th>SU</th><th>ATS</th><th>O/U</th>
            <th style={{ textAlign: 'left' }}>ATS SCORECARD</th>
          </tr>
        </thead>
        <tbody>
          {schedule.map((g) => (
            <tr key={g.id}>
              <td style={{ fontFamily: 'Barlow Condensed', fontWeight: 600 }}>{g.game_date}</td>
              <td style={{ textAlign: 'left', fontFamily: 'Barlow Condensed' }}>
                {!g.is_home && <span style={{ color: 'var(--text-muted)', marginRight: 4 }}>at</span>}
                {g.opponent}
              </td>
              <td style={{ color: 'var(--text-muted)' }}>{g.opp_record || '–'}</td>
              {league === 'NFL' && <td style={{ color: 'var(--text-accent)', fontWeight: 600 }}>{fmtSpread(g.adv)}</td>}
              <td>{g.points_for ?? '–'}</td>
              <td>{g.points_against ?? '–'}</td>
              {league === 'NFL' && <td style={{ color: 'var(--text-secondary)' }}>{fmtSpread(g.line)}</td>}
              <td>{g.su_result ? <span className={g.su_result === 'W' ? 'win' : 'loss'}>{g.su_result}</span> : '–'}</td>
              <td>{g.ats_result ? <span className={g.ats_result === 'W' ? 'win' : g.ats_result === 'L' ? 'loss' : 'push'}>{g.ats_result}</span> : '–'}</td>
              <td>{g.ou_result || '–'}</td>
              <td style={{ textAlign: 'left', fontSize: '0.75rem', color: 'var(--text-muted)' }}>{g.ats_scorecard || ''}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/* ── Game Logs Table ───────────────────────────────────────── */
function GameLogsTable({ gamelogs }) {
  return (
    <div style={{ overflowX: 'auto' }}>
      <table className="stat-table">
        <thead>
          <tr>
            <th>#</th><th>DATE</th>
            <th style={{ textAlign: 'left' }}>OPPONENT</th>
            <th>OWL</th><th>PF</th><th>PA</th><th>SU</th><th>LINE</th><th>ATS</th><th>O/U</th>
            <th>OYP</th><th>OFR</th><th>OFP</th><th>OYD</th>
            <th>DYD</th><th>DFP</th><th>DFR</th><th>DYP</th>
            <th>RES</th><th>F-A</th>
          </tr>
        </thead>
        <tbody>
          {gamelogs.map((g) => (
            <tr key={g.id}>
              <td style={{ color: 'var(--text-muted)' }}>{g.game_num}</td>
              <td style={{ fontFamily: 'Barlow Condensed', fontWeight: 600 }}>{g.game_date}</td>
              <td style={{ textAlign: 'left', fontFamily: 'Barlow Condensed' }}>
                {!g.is_home && <span style={{ color: 'var(--text-muted)', marginRight: 4 }}>at</span>}
                {g.opponent}
              </td>
              <td style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>{g.opp_record || '–'}</td>
              <td style={{ color: 'var(--text-win)', fontWeight: 600 }}>{g.points_for ?? '–'}</td>
              <td style={{ color: 'var(--text-loss)', fontWeight: 600 }}>{g.points_against ?? '–'}</td>
              <td>{g.su_result ? <span className={g.su_result === 'W' ? 'win' : 'loss'}>{g.su_result}</span> : '–'}</td>
              <td style={{ color: 'var(--text-accent)' }}>
                {g.line != null ? (g.line > 0 ? `+${g.line}` : g.line === 0 ? 'PK' : g.line) : '–'}
              </td>
              <td>{g.ats_result ? <span className={g.ats_result === 'W' ? 'win' : g.ats_result === 'L' ? 'loss' : 'push'}>{g.ats_result}</span> : '–'}</td>
              <td style={{ fontSize: '0.75rem' }}>{g.ou_result || '–'}{g.ou_line ? g.ou_line : ''}</td>
              <td>{g.off_ypr ?? '–'}</td>
              <td>{g.off_rush ?? '–'}</td>
              <td>{g.off_pass ?? '–'}</td>
              <td style={{ fontWeight: 600 }}>{g.off_total ?? '–'}</td>
              <td style={{ fontWeight: 600 }}>{g.def_total ?? '–'}</td>
              <td>{g.def_pass ?? '–'}</td>
              <td>{g.def_rush ?? '–'}</td>
              <td>{g.def_ypr ?? '–'}</td>
              <td style={{ fontSize: '0.75rem' }}>{g.result_score || '–'}</td>
              <td style={{ fontSize: '0.75rem' }}>{g.first_downs || '–'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/* ── Trends Panel ──────────────────────────────────────────── */
function TrendsPanel({ trends, league }) {
  const sections = league === 'CFB'
    ? [
        { key: 'good_trends', label: 'THE GOOD', bg: 'var(--good-bg)',  accent: '#2e7d32' },
        { key: 'bad_trends',  label: 'THE BAD',  bg: 'var(--bad-bg)',   accent: '#e65100' },
        { key: 'ugly_trends', label: 'THE UGLY', bg: 'var(--ugly-bg)',  accent: '#880e4f' },
      ]
    : [
        { key: 'good_trends', label: 'THE GOOD',   bg: 'var(--good-bg)',       accent: '#2e7d32' },
        { key: 'bad_trends',  label: 'THE BAD',    bg: 'var(--bad-bg)',        accent: '#e65100' },
        { key: 'ugly_trends', label: 'THE UGLY',   bg: 'var(--ugly-bg)',       accent: '#880e4f' },
        { key: 'ou_trends',   label: 'OVER/UNDER', bg: 'var(--bg-table-alt)', accent: 'var(--border-accent)' },
      ]

  return (
    <div className="card" style={{ overflow: 'hidden' }}>
      <div className="section-title">
        {league === 'CFB' ? 'MARC LAWRENCE TEAM TRENDS' : 'BEST & WORST TEAM TRENDS'}
      </div>
      {sections.map(({ key, label, bg, accent }) => {
        const text = trends[key]
        if (!text) return null
        return (
          <div key={key} style={{ borderBottom: '1px solid var(--border)' }}>
            <div style={{ background: bg, padding: '6px 12px', fontFamily: 'Oswald, sans-serif', fontSize: '0.8rem', fontWeight: '600', letterSpacing: '0.08em', color: accent, borderLeft: `3px solid ${accent}` }}>{label}</div>
            <div style={{ padding: '10px 12px' }}>
              {text.split('\n').filter(Boolean).map((line, i) => (
                <div key={i} style={{ fontFamily: 'Barlow Condensed, sans-serif', fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.5, paddingLeft: '8px' }}>{line}</div>
              ))}
            </div>
          </div>
        )
      })}
    </div>
  )
}

/* ── CFB Playbook Panel ────────────────────────────────────── */
function CFBPlaybookPanel({ playbook }) {
  return (
    <div className="card" style={{ overflow: 'hidden' }}>
      <div className="section-title">2025 PLAYBOOK</div>

      {/* Team Theme */}
      {playbook.team_theme && (
        <div style={{ padding: '10px 16px', borderBottom: '1px solid var(--border)', fontFamily: 'Oswald, sans-serif', fontSize: '1rem', fontWeight: 700, color: 'var(--text-accent)', letterSpacing: '0.08em' }}>
          TEAM THEME: {playbook.team_theme}
        </div>
      )}

      {/* Narrative */}
      {playbook.narrative && (
        <div style={{ padding: '14px 16px', borderBottom: '1px solid var(--border)', borderLeft: '3px solid var(--border-accent)' }}>
          <div style={{ fontFamily: 'Barlow, sans-serif', fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.7 }}>
            {playbook.narrative}
          </div>
        </div>
      )}

      {/* Stat You Will Like */}
      {playbook.stat_you_will_like && (
        <div style={{ margin: '12px 16px', padding: '10px 12px', background: '#0a1a0a', borderRadius: '4px', border: '1px solid #2e7d3244' }}>
          <div style={{ fontFamily: 'Oswald', fontSize: '0.72rem', fontWeight: 700, color: '#4caf50', letterSpacing: '0.08em', marginBottom: '6px' }}>STAT YOU WILL LIKE</div>
          <div style={{ fontFamily: 'Barlow Condensed', fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
            {playbook.stat_you_will_like}
          </div>
        </div>
      )}

      {/* Pointspread Power Play */}
      {playbook.power_play && (
        <div style={{ margin: '12px 16px 16px', padding: '10px 12px', background: '#1a1500', borderRadius: '4px', border: '1px solid #FFD70044' }}>
          <div style={{ fontFamily: 'Oswald', fontSize: '0.72rem', fontWeight: 700, color: '#FFD700', letterSpacing: '0.08em', marginBottom: '6px' }}>POINTSPREAD POWER PLAY</div>
          {playbook.power_play.split('\n').filter(Boolean).map((line, i) => (
            <div key={i} style={{ fontFamily: 'Barlow Condensed', fontSize: '0.9rem', color: '#FFD700', fontWeight: 600, lineHeight: 1.5 }}>{line}</div>
          ))}
        </div>
      )}
    </div>
  )
}

/* ── NFL Playbook Panel ────────────────────────────────────── */
function NFLPlaybookPanel({ playbook }) {
  const TrendLines = ({ text }) => {
    if (!text) return null
    return (
      <div>
        {text.split('\n').filter(Boolean).map((line, i) => (
          <div key={i} style={{ fontFamily: 'Barlow Condensed, sans-serif', fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.6, textAlign: 'center' }}>{line}</div>
        ))}
      </div>
    )
  }

  const SectionTitle = ({ children }) => (
    <div style={{ fontFamily: 'Oswald, sans-serif', fontSize: '0.8rem', fontWeight: 700, letterSpacing: '0.1em', color: 'var(--text-accent)', textAlign: 'center', marginBottom: '6px', paddingBottom: '4px', borderBottom: '1px solid var(--border)' }}>
      {children}
    </div>
  )

  const SubTitle = ({ children }) => (
    <div style={{ fontFamily: 'Barlow Condensed, sans-serif', fontSize: '0.65rem', color: 'var(--text-muted)', textAlign: 'center', letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: '8px' }}>
      {children}
    </div>
  )

  const QtrTitle = ({ children }) => (
    <div style={{ fontFamily: 'Oswald, sans-serif', fontSize: '0.72rem', fontWeight: 700, letterSpacing: '0.08em', color: 'var(--text-secondary)', textAlign: 'center', marginTop: '10px', marginBottom: '4px' }}>
      {children}
    </div>
  )

  return (
    <div className="card" style={{ overflow: 'hidden' }}>
      <div className="section-title">2025 PLAYBOOK</div>
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 3fr', gap: '0' }}>

        {/* LEFT */}
        <div style={{ padding: '16px 20px', borderRight: '1px solid var(--border)' }}>
          <div style={{ marginBottom: '24px' }}>
            <SectionTitle>COACHES CORNER</SectionTitle>
            <SubTitle>(CAREER HISTORY RESULTS INCLUDING PLAYOFFS)</SubTitle>
            {playbook.coaches_corner && (
              <div style={{ fontFamily: 'Oswald, sans-serif', fontSize: '0.85rem', color: 'var(--text-accent)', textAlign: 'center', marginBottom: '6px' }}>
                {playbook.coaches_corner.split('\n')[0]}
              </div>
            )}
            <TrendLines text={playbook.coaches_corner?.split('\n').slice(1).join('\n')} />
          </div>
          <div style={{ marginBottom: '24px' }}>
            <SectionTitle>QUARTERLY REPORT</SectionTitle>
            {playbook.q1_trends && <><QtrTitle>1ST QTR: GAMES 1-4</QtrTitle><TrendLines text={playbook.q1_trends} /></>}
            {playbook.q2_trends && <><QtrTitle>2ND QTR: GAMES 5-8</QtrTitle><TrendLines text={playbook.q2_trends} /></>}
            {playbook.q3_trends && <><QtrTitle>3RD QTR: GAMES 9-12</QtrTitle><TrendLines text={playbook.q3_trends} /></>}
            {playbook.q4_trends && <><QtrTitle>4TH QTR: GAMES 13-17</QtrTitle><TrendLines text={playbook.q4_trends} /></>}
          </div>
          <div>
            <SectionTitle>DIVISION DATA</SectionTitle>
            <SubTitle>(RESULTS VS REGULAR SEASON DIVISION OPPS)</SubTitle>
            <TrendLines text={playbook.division_data} />
          </div>
        </div>

        {/* RIGHT */}
        <div style={{ padding: '16px 20px' }}>
          {playbook.team_theme && (
            <div style={{ textAlign: 'right', marginBottom: '12px' }}>
              <div style={{ fontFamily: 'Barlow Condensed, sans-serif', fontSize: '0.65rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em' }}>Team Theme</div>
              <div style={{ fontFamily: 'Oswald, sans-serif', fontSize: '1rem', fontWeight: 700, color: 'var(--text-accent)', letterSpacing: '0.06em' }}>{playbook.team_theme}</div>
            </div>
          )}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginBottom: '8px' }}>
            {playbook.win_total && (
              <div style={{ background: 'var(--bg-table-alt)', borderRadius: '4px', padding: '8px 10px', textAlign: 'center' }}>
                <div style={{ fontFamily: 'Barlow Condensed', fontSize: '0.62rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Win Total</div>
                <div style={{ fontFamily: 'Oswald', fontSize: '1.1rem', color: 'var(--text-accent)', fontWeight: 700 }}>
                  {playbook.win_total} <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>({playbook.win_total_odds})</span>
                </div>
              </div>
            )}
            {playbook.opp_win_total && (
              <div style={{ background: 'var(--bg-table-alt)', borderRadius: '4px', padding: '8px 10px', textAlign: 'center' }}>
                <div style={{ fontFamily: 'Barlow Condensed', fontSize: '0.62rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Opp Win Total</div>
                <div style={{ fontFamily: 'Oswald', fontSize: '1.1rem', color: 'var(--text-accent)', fontWeight: 700 }}>{playbook.opp_win_total}</div>
              </div>
            )}
          </div>
          {playbook.playoff_yes_odds && (
            <div style={{ background: 'var(--bg-table-alt)', borderRadius: '4px', padding: '8px 10px', textAlign: 'center', marginBottom: '14px' }}>
              <div style={{ fontFamily: 'Barlow Condensed', fontSize: '0.62rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '4px' }}>Playoffs</div>
              <div style={{ fontFamily: 'Oswald', fontSize: '0.9rem', fontWeight: 600 }}>
                <span style={{ color: 'var(--text-win)' }}>YES {playbook.playoff_yes_odds}</span>
                <span style={{ color: 'var(--text-muted)', margin: '0 8px' }}>•</span>
                <span style={{ color: 'var(--text-loss)' }}>NO {playbook.playoff_no_odds}</span>
              </div>
            </div>
          )}
          {playbook.narrative && (
            <div style={{ marginBottom: '14px', padding: '10px 12px', background: 'var(--bg-table-alt)', borderRadius: '4px', borderLeft: '3px solid var(--border-accent)' }}>
              <div style={{ fontFamily: 'Barlow, sans-serif', fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.7 }}>
                {playbook.narrative}
              </div>
            </div>
          )}
          {playbook.stat_you_will_like && (
            <div style={{ marginBottom: '14px', padding: '10px 12px', background: '#0a1a0a', borderRadius: '4px', border: '1px solid #2e7d3244' }}>
              <div style={{ fontFamily: 'Oswald', fontSize: '0.72rem', fontWeight: 700, color: '#4caf50', letterSpacing: '0.08em', marginBottom: '6px' }}>STAT YOU WILL LIKE</div>
              <div style={{ fontFamily: 'Barlow Condensed', fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>{playbook.stat_you_will_like}</div>
            </div>
          )}
          {playbook.power_play && (
            <div style={{ marginBottom: '14px', padding: '10px 12px', background: '#1a1500', borderRadius: '4px', border: '1px solid #FFD70044' }}>
              <div style={{ fontFamily: 'Oswald', fontSize: '0.72rem', fontWeight: 700, color: '#FFD700', letterSpacing: '0.08em', marginBottom: '6px' }}>POINTSPREAD POWER PLAY</div>
              {playbook.power_play.split('\n').filter(Boolean).map((line, i) => (
                <div key={i} style={{ fontFamily: 'Barlow Condensed', fontSize: '0.9rem', color: '#FFD700', fontWeight: 600, lineHeight: 1.5 }}>{line}</div>
              ))}
            </div>
          )}
          <div style={{ border: '1px solid var(--border)', borderRadius: '4px', overflow: 'hidden' }}>
            <div style={{ background: 'var(--text-accent)', padding: '8px', textAlign: 'center' }}>
              <div style={{ fontFamily: 'Oswald, sans-serif', fontSize: '0.85rem', fontWeight: 700, color: '#000', letterSpacing: '0.1em' }}>NOTES</div>
            </div>
            {[...Array(10)].map((_, i) => (
              <div key={i} style={{ borderBottom: '1px solid var(--border)', height: '28px', background: i % 2 === 0 ? 'transparent' : '#ffffff04' }} />
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

/* ── ATS History Table ─────────────────────────────────────── */
function ATSHistoryTable({ history, league }) {
  if (!history.length) return (
    <div style={{ padding: '20px', textAlign: 'center', color: 'var(--text-muted)' }}>No data available</div>
  )

  const fmtLine = (v) => v != null ? (v > 0 ? `+${v}` : v === 0 ? 'PK' : v) : '–'

  return (
    <div style={{ overflowX: 'auto' }}>
      <table className="stat-table">
        <thead>
          <tr>
            <th>#</th>
            <th style={{ textAlign: 'left' }}>OPPONENT</th>
            <th>SCORE</th>
            <th>SU</th>
            <th>LINE</th>
            <th>ATS</th>
            {league === 'NFL' && <th>O/U</th>}
          </tr>
        </thead>
        <tbody>
          {history.map((g) => (
            <tr key={g.id} style={{ background: g.is_playoff ? '#1a1a00' : 'transparent' }}>
              <td style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>
                {g.is_playoff ? 'PL' : g.game_num}
              </td>
              <td style={{ textAlign: 'left', fontFamily: 'Barlow Condensed' }}>
                {!g.is_home && !g.is_neutral && <span style={{ color: 'var(--text-muted)', marginRight: 4 }}>at</span>}
                {g.is_neutral && <span style={{ color: '#888', marginRight: 4 }}>n</span>}
                {g.opponent}
              </td>
              <td style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                {g.points_for != null ? `${g.points_for}-${g.points_against}` : '–'}
              </td>
              <td>{g.su_result ? <span className={g.su_result === 'W' ? 'win' : g.su_result === 'L' ? 'loss' : 'push'}>{g.su_result}</span> : '–'}</td>
              <td style={{ color: 'var(--text-accent)' }}>{fmtLine(g.line)}</td>
              <td>{g.ats_result ? <span className={g.ats_result === 'W' ? 'win' : g.ats_result === 'L' ? 'loss' : 'push'}>{g.ats_result}</span> : '–'}</td>
              {league === 'NFL' && (
                <td style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  {g.ou_result ? `${g.ou_result}${g.ou_line || ''}` : '–'}
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/* ── Draft Picks Table ─────────────────────────────────────── */
function DraftPicksTable({ picks }) {
  return (
    <div style={{ overflowX: 'auto' }}>
      <table className="stat-table">
        <thead>
          <tr>
            <th>RD</th>
            <th style={{ textAlign: 'left' }}>PLAYER</th>
            <th>POS</th><th>HT</th><th>WT</th>
            <th style={{ textAlign: 'left' }}>COLLEGE</th>
          </tr>
        </thead>
        <tbody>
          {picks.map((p) => (
            <tr key={p.id}>
              <td style={{ color: 'var(--text-accent)', fontWeight: 600 }}>{p.round_num}</td>
              <td style={{ textAlign: 'left', fontFamily: 'Barlow Condensed', fontWeight: 600 }}>{p.player_name}</td>
              <td style={{ color: 'var(--text-secondary)' }}>{p.position}</td>
              <td style={{ color: 'var(--text-muted)' }}>{p.height}</td>
              <td style={{ color: 'var(--text-muted)' }}>{p.weight}</td>
              <td style={{ textAlign: 'left', color: 'var(--text-secondary)' }}>{p.college}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
