import React, { useState, useEffect, useCallback, useRef } from 'react'

const API = import.meta.env.VITE_API_URL || '/api'

/* ──────────── Theme Hook ──────────── */
function useTheme() {
  const [theme, setThemeState] = useState(() => {
    return localStorage.getItem('admin_theme') || 'dark'
  })
  useEffect(() => {
    document.documentElement.setAttribute('data-admin-theme', theme)
    localStorage.setItem('admin_theme', theme)
  }, [theme])
  const toggleTheme = useCallback(() => {
    setThemeState(t => (t === 'dark' ? 'light' : 'dark'))
  }, [])
  return [theme, toggleTheme]
}

/* ──────────── Icons (inline SVG) ──────────── */
const Icon = ({ name, size = 18 }) => {
  const icons = {
    dashboard: <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>,
    users: <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>,
    billing: <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="M12 9v6"/><path d="M9 12h6"/></svg>,
    monitor: <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>,
    config: <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="3"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>,
    logs: <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>,
    voice: <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/></svg>,
    admin: <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>,
    sun: <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>,
    moon: <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>,
    play: <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" stroke="none"><polygon points="5 3 19 12 5 21 5 3"/></svg>,
    stop: <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" stroke="none"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>,
    search: <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>,
  }
  return icons[name] || null
}

/* ──────────── Sidebar ──────────── */
function Sidebar({ tabs, activeTab, onTabChange, collapsed, onToggle }) {
  return (
    <aside className={`admin-sidebar ${collapsed ? 'collapsed' : ''}`}>
      <div className="sidebar-header">
        {!collapsed && <span className="sidebar-logo">⚙️ Console</span>}
        <button className="sidebar-toggle" onClick={onToggle}>
          {collapsed ? '☰' : '✕'}
        </button>
      </div>
      <nav className="sidebar-nav">
        {tabs.map(tab => (
          <button
            key={tab.id}
            className={`sidebar-item ${activeTab === tab.id ? 'active' : ''}`}
            onClick={() => onTabChange(tab.id)}
            title={tab.label}
          >
            <Icon name={tab.icon} size={20} />
            {!collapsed && <span className="sidebar-label">{tab.label}</span>}
          </button>
        ))}
      </nav>
      <div className="sidebar-footer">
        {!collapsed && <span className="sidebar-version">v0.1.0</span>}
      </div>
    </aside>
  )
}

/* ──────────── KPI Card ──────────── */
function KPICard({ label, value, sub, icon, color }) {
  return (
    <div className="kpi-card" style={{ borderLeft: `3px solid ${color}` }}>
      <div className="kpi-icon" style={{ color }}>{icon}</div>
      <div className="kpi-content">
        <div className="kpi-label">{label}</div>
        <div className="kpi-value">{value ?? '—'}</div>
        {sub && <div className="kpi-sub">{sub}</div>}
      </div>
    </div>
  )
}

/* ──────────── Overview Tab ──────────── */
function OverviewTab({ overview }) {
  if (!overview) {
    return <div className="tab-loading">Loading overview...</div>
  }
  const cards = [
    { label: 'Total Users', value: overview.total_users ?? 0, icon: '👥', color: '#3b82f6' },
    { label: 'Today Meals', value: overview.today_meals ?? 0, icon: '🍽️', color: '#22c55e' },
    { label: 'Active Subs', value: overview.active_subscriptions ?? 0, icon: '⭐', color: '#f59e0b' },
    { label: 'API Calls (24h)', value: overview.api_calls_24h ?? 0, icon: '📡', color: '#8b5cf6' },
    { label: 'Revenue (MTD)', value: overview.revenue_mtd != null ? `$${overview.revenue_mtd}` : '$0', icon: '💰', color: '#10b981' },
    { label: 'Pending Orders', value: overview.pending_invoices ?? 0, icon: '📋', color: '#ef4444' },
  ]

  return (
    <div className="tab-content">
      <div className="kpi-grid">
        {cards.map((c, i) => <KPICard key={i} {...c} />)}
      </div>
    </div>
  )
}

/* ──────────── Audit Logs Tab ──────────── */
function AuditLogsTab({ fetchWithAdmin }) {
  const [logs, setLogs] = useState([])
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(false)

  const loadLogs = useCallback(async () => {
    setLoading(true)
    try {
      const data = await fetchWithAdmin('/logs')
      if (data?.logs) setLogs(data.logs)
    } catch {}
    setLoading(false)
  }, [fetchWithAdmin])

  useEffect(() => { loadLogs() }, [loadLogs])

  const filtered = search
    ? logs.filter(l =>
        (l.action || '').toLowerCase().includes(search.toLowerCase()) ||
        (l.admin_id || '').toLowerCase().includes(search.toLowerCase()) ||
        (l.target_type || '').toLowerCase().includes(search.toLowerCase())
      )
    : logs

  return (
    <div className="tab-content">
      <div className="logs-toolbar">
        <div className="search-box">
          <Icon name="search" size={14} />
          <input
            type="text"
            placeholder="Search logs..."
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
        <button className="btn btn-sm" onClick={loadLogs}>🔄 Refresh</button>
      </div>
      <div className="table-wrapper">
        <table className="data-table">
          <thead>
            <tr>
              <th>Time</th>
              <th>Admin</th>
              <th>Action</th>
              <th>Target</th>
              <th>Details</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 && (
              <tr><td colSpan={5} className="table-empty">{loading ? 'Loading...' : 'No logs found'}</td></tr>
            )}
            {filtered.map(log => (
              <tr key={log.id}>
                <td className="cell-time">{new Date(log.created_at).toLocaleString()}</td>
                <td><code>{log.admin_id}</code></td>
                <td><span className={`badge badge-${log.action}`}>{log.action}</span></td>
                <td>{log.target_type}/{log.target_id}</td>
                <td className="cell-details">{log.details ? JSON.stringify(log.details).slice(0, 60) : ''}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

/* ──────────── TTS Test Tab ──────────── */
function TTSTab({ fetchWithAdmin }) {
  const [voices, setVoices] = useState([])
  const [text, setText] = useState('你好，欢迎使用 AI 卡路里助手！')
  const [selectedVoice, setSelectedVoice] = useState('zh-CN-XiaoxiaoNeural')
  const [rate, setRate] = useState('+0%')
  const [playing, setPlaying] = useState(false)
  const [error, setError] = useState('')
  const audioRef = useRef(null)

  useEffect(() => {
    fetchWithAdmin('/tts/voices').then(data => {
      if (data?.voices) setVoices(data.voices)
    }).catch(() => {})
  }, [fetchWithAdmin])

  const handleSynthesize = async () => {
    if (!text.trim()) return
    setError('')
    setPlaying(true)
    try {
      const adminId = JSON.parse(sessionStorage.getItem('admin_session') || '{}').adminId
      const r = await fetch(`${API}/api/v1/admin/tts/synthesize?admin_id=${adminId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, voice: selectedVoice, rate, pitch: '+0Hz' }),
      })
      if (!r.ok) {
        const errText = await r.text()
        setError(`TTS failed: ${errText.slice(0, 100)}`)
        setPlaying(false)
        return
      }
      const blob = await r.blob()
      const url = URL.createObjectURL(blob)
      if (audioRef.current) {
        audioRef.current.src = url
        audioRef.current.play().catch(() => {})
        audioRef.current.onended = () => setPlaying(false)
      }
    } catch (e) {
      setError(`Error: ${e.message}`)
      setPlaying(false)
    }
  }

  return (
    <div className="tab-content">
      <div className="tts-card">
        <h3 className="section-title">🔊 Edge-TTS 语音合成测试</h3>
        <div className="tts-form">
          <div className="form-group">
            <label>Voice</label>
            <select value={selectedVoice} onChange={e => setSelectedVoice(e.target.value)}>
              {voices.map(v => (
                <option key={v.id} value={v.id}>{v.name} ({v.id})</option>
              ))}
            </select>
          </div>
          <div className="form-group">
            <label>Rate: {rate}</label>
            <input type="range" min="-50" max="50" value={parseInt(rate)} onChange={e => setRate(`${e.target.value}%`)} />
          </div>
          <div className="form-group full-width">
            <label>Text (max 500 chars)</label>
            <textarea
              value={text}
              onChange={e => setText(e.target.value)}
              maxLength={500}
              rows={3}
              placeholder="Enter text to synthesize..."
            />
            <span className="char-count">{text.length}/500</span>
          </div>
          {error && <div className="tts-error">{error}</div>}
          <div className="tts-actions">
            <button className="btn btn-primary" onClick={handleSynthesize} disabled={playing || !text.trim()}>
              <Icon name={playing ? 'stop' : 'play'} size={16} />
              {playing ? 'Playing...' : 'Play'}
            </button>
            <audio ref={audioRef} controls style={{ marginLeft: 12, height: 32 }} />
          </div>
        </div>
      </div>
    </div>
  )
}

/* ──────────── Main Admin Console ──────────── */
export default function AdminConsole({ session, onLogout }) {
  const [theme, toggleTheme] = useTheme()
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [activeTab, setActiveTab] = useState('overview')
  const [overview, setOverview] = useState(null)

  const adminId = session?.adminId || ''

  const fetchWithAdmin = useCallback(async (endpoint, opts = {}) => {
    const params = new URLSearchParams({ admin_id: adminId, ...opts })
    const r = await fetch(`${API}/api/v1/admin${endpoint}?${params}`)
    if (!r.ok) throw new Error(`HTTP ${r.status}`)
    return r.json()
  }, [adminId])

  useEffect(() => {
    if (activeTab === 'overview') {
      fetchWithAdmin('/overview').then(d => setOverview(d.overview)).catch(() => {})
    }
  }, [activeTab, fetchWithAdmin])

  const tabs = [
    { id: 'overview', label: 'Dashboard', icon: 'dashboard' },
    { id: 'logs', label: 'Audit Logs', icon: 'logs' },
    { id: 'tts', label: 'TTS Test', icon: 'voice' },
  ]

  return (
    <div className={`admin-console theme-${theme}`}>
      <Sidebar
        tabs={tabs}
        activeTab={activeTab}
        onTabChange={setActiveTab}
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed(c => !c)}
      />
      <div className="console-main">
        <header className="console-navbar">
          <div className="navbar-left">
            <h1 className="navbar-title">AI Calorie Assistant Console</h1>
          </div>
          <div className="navbar-right">
            <button className="btn-icon" onClick={toggleTheme} title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}>
              <Icon name={theme === 'dark' ? 'sun' : 'moon'} size={18} />
            </button>
            <span className="navbar-user">
              <Icon name="admin" size={16} />
              {session.username} ({session.role})
            </span>
            <button className="btn btn-outline btn-sm" onClick={onLogout}>Logout</button>
          </div>
        </header>
        <div className="console-body">
          {activeTab === 'overview' && <OverviewTab overview={overview} />}
          {activeTab === 'logs' && <AuditLogsTab fetchWithAdmin={fetchWithAdmin} />}
          {activeTab === 'tts' && <TTSTab fetchWithAdmin={fetchWithAdmin} />}
        </div>
      </div>
    </div>
  )
}
