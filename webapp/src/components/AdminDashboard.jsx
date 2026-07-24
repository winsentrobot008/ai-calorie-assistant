import React, { useState, useEffect } from 'react'

const ADMIN_API = import.meta.env.VITE_API_URL || '/api'

function StatCard({ label, value, sub, color }) {
  return (
    <div className="admin-stat-card" style={{ borderLeft: `3px solid ${color}` }}>
      <div className="admin-stat-label">{label}</div>
      <div className="admin-stat-value">{value}</div>
      {sub && <div className="admin-stat-sub">{sub}</div>}
    </div>
  )
}

export default function AdminDashboard({ session, onLogout }) {
  const [tab, setTab] = useState('overview')
  const [overview, setOverview] = useState(null)
  const [users, setUsers] = useState([])
  const [revenue, setRevenue] = useState(null)
  const [modelData, setModelData] = useState(null)
  const [config, setConfig] = useState({})
  const [configKey, setConfigKey] = useState('')
  const [configValue, setConfigValue] = useState('')
  const [auditLogs, setAuditLogs] = useState([])
  const [loading, setLoading] = useState(false)

  const fetchData = async (endpoint, setter) => {
    setLoading(true)
    try {
      const r = await fetch(`${ADMIN_API}/api/v1/admin${endpoint}`)
      if (r.ok) setter(await r.json())
    } catch {}
    setLoading(false)
  }

  useEffect(() => {
    if (tab === 'overview') fetchData('/overview', d => setOverview(d.overview))
    else if (tab === 'users') fetchData('/users', d => setUsers(d.users || []))
    else if (tab === 'revenue') fetchData('/revenue?period=monthly', d => setRevenue(d))
    else if (tab === 'models') fetchData('/model-monitor?hours=24', d => setModelData(d))
    else if (tab === 'config') fetchData('/config', d => setConfig(d.config || {}))
    else if (tab === 'logs') fetchData('/logs', d => setAuditLogs(d.logs || []))
  }, [tab])

  const handleSetConfig = async () => {
    if (!configKey) return
    const params = new URLSearchParams({ key: configKey, value: configValue, admin_id: session.adminId })
    await fetch(`${ADMIN_API}/api/v1/admin/config?${params}`, { method: 'POST' })
    fetchData('/config', d => setConfig(d.config || {}))
    setConfigKey('')
    setConfigValue('')
  }

  return (
    <div className="admin-dashboard">
      {/* Admin Header */}
      <div className="admin-header">
        <h2>⚙️ 管理后台</h2>
        <div className="admin-header-right">
          <span className="admin-user">{session.username} ({session.role})</span>
          <button className="admin-logout-btn" onClick={onLogout}>退出</button>
        </div>
      </div>

      {/* Admin Tabs */}
      <div className="admin-tabs">
        {[
          { id: 'overview', label: '系统总览' },
          { id: 'users', label: '用户管理' },
          { id: 'revenue', label: '收益统计' },
          { id: 'models', label: '模型监控' },
          { id: 'config', label: '配置中心' },
          { id: 'logs', label: '日志中心' },
        ].map(t => (
          <button key={t.id}
            className={`admin-tab ${tab === t.id ? 'active' : ''}`}
            onClick={() => setTab(t.id)}>
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="admin-content">
        {loading && <div className="admin-loading">加载中...</div>}

        {/* ── Overview ── */}
        {tab === 'overview' && overview && (
          <div className="admin-overview-grid">
            <StatCard label="总用户数" value={overview.total_users} color="#60a5fa" />
            <StatCard label="今日识别" value={overview.today_recognitions} sub={`本周: ${overview.weekly_recognitions}`} color="#34d399" />
            <StatCard label="活跃订阅" value={overview.active_subscriptions} sub={`永久买断: ${overview.permanent_licenses}`} color="#fbbf24" />
            <StatCard label="模型调用(24h)" value={overview.model_calls_24h} color="#a78bfa" />
            <StatCard label="错误率" value={`${overview.error_rate_pct}%`} sub={`错误: ${overview.model_errors_24h}`} color="#ef4444" />
            <StatCard label="总收入" value={`$${overview.total_revenue}`} color="#f59e0b" />
          </div>
        )}

        {/* ── Users ── */}
        {tab === 'users' && (
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>名称</th>
                  <th>订阅</th>
                  <th>买断</th>
                  <th>免费次/广告</th>
                  <th>状态</th>
                </tr>
              </thead>
              <tbody>
                {users.map(u => (
                  <tr key={u.id}>
                    <td className="admin-cell-id">{u.id.slice(0, 8)}...</td>
                    <td>{u.name || u.email || '-'}</td>
                    <td>
                      <span className={`admin-status ${u.subscription_status === 'active' ? 'active' : ''}`}>
                        {u.subscription_status}
                      </span>
                      {u.subscription_plan && <span style={{ fontSize: 11, marginLeft: 4, color: '#94a3b8' }}>{u.subscription_plan}</span>}
                    </td>
                    <td>{u.license_type === 'permanent' ? '✅ 永久' : '-'}</td>
                    <td style={{ fontSize: 12 }}>
                      <span>免费: {u.daily_free_uses ?? 1}</span>
                      {u.ad_reward_credits > 0 && <span className="ad-credit-badge-admin"> +{u.ad_reward_credits}广告</span>}
                    </td>
                    <td>{u.is_active ? '正常' : '封禁'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* ── Revenue ── */}
        {tab === 'revenue' && revenue && (
          <div className="admin-revenue">
            <div className="admin-overview-grid">
              <StatCard label="总收入" value={`$${revenue.total_revenue}`} color="#f59e0b" />
              <StatCard label="订阅收入" value={`$${revenue.breakdown?.subscription || 0}`} color="#60a5fa" />
              <StatCard label="买断收入" value={`$${revenue.breakdown?.license || 0}`} color="#a78bfa" />
              <StatCard label="发票数" value={revenue.invoice_count} color="#34d399" />
            </div>
            <div className="admin-revenue-breakdown">
              <h4>方案明细</h4>
              <div className="admin-breakdown-bars">
                <div className="breakdown-item">
                  <span>月付</span>
                  <div className="breakdown-bar-bg">
                    <div className="breakdown-bar-fill" style={{ width: `${Math.min((revenue.plan_breakdown?.monthly || 0) / Math.max(revenue.total_revenue, 1) * 100, 100)}%`, background: '#f59e0b' }} />
                  </div>
                  <span>${revenue.plan_breakdown?.monthly || 0}</span>
                </div>
                <div className="breakdown-item">
                  <span>年付</span>
                  <div className="breakdown-bar-bg">
                    <div className="breakdown-bar-fill" style={{ width: `${Math.min((revenue.plan_breakdown?.yearly || 0) / Math.max(revenue.total_revenue, 1) * 100, 100)}%`, background: '#60a5fa' }} />
                  </div>
                  <span>${revenue.plan_breakdown?.yearly || 0}</span>
                </div>
                <div className="breakdown-item">
                  <span>永久</span>
                  <div className="breakdown-bar-bg">
                    <div className="breakdown-bar-fill" style={{ width: `${Math.min((revenue.plan_breakdown?.permanent || 0) / Math.max(revenue.total_revenue, 1) * 100, 100)}%`, background: '#a78bfa' }} />
                  </div>
                  <span>${revenue.plan_breakdown?.permanent || 0}</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ── Model Monitor ── */}
        {tab === 'models' && modelData && (
          <div>
            <p className="admin-subtitle">24 小时内模型调用统计 (共 {modelData.total_calls} 次)</p>
            <div className="admin-table-wrap">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>模型</th>
                    <th>调用次数</th>
                    <th>错误</th>
                    <th>错误率</th>
                    <th>平均延迟</th>
                    <th>Token 消耗</th>
                  </tr>
                </thead>
                <tbody>
                  {(modelData.models || []).map(m => (
                    <tr key={m.name}>
                      <td>{m.name}</td>
                      <td>{m.calls}</td>
                      <td style={{ color: m.errors > 0 ? '#ef4444' : '#34d399' }}>{m.errors}</td>
                      <td>{m.error_rate_pct}%</td>
                      <td>{m.avg_latency_ms}ms</td>
                      <td>{m.total_tokens}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* ── Config ── */}
        {tab === 'config' && (
          <div>
            <div className="admin-config-form">
              <h4>添加 / 更新配置</h4>
              <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                <input className="form-input" style={{ flex: 1 }} placeholder="配置键 (key)"
                  value={configKey} onChange={e => setConfigKey(e.target.value)} />
                <input className="form-input" style={{ flex: 1 }} placeholder="配置值 (value)"
                  value={configValue} onChange={e => setConfigValue(e.target.value)} />
                <button className="submit-btn" style={{ width: 'auto', padding: '0 20px' }}
                  onClick={handleSetConfig}>设置</button>
              </div>
            </div>
            <div className="admin-table-wrap" style={{ marginTop: 16 }}>
              <table className="admin-table">
                <thead>
                  <tr><th>配置键</th><th>配置值</th></tr>
                </thead>
                <tbody>
                  {Object.entries(config).map(([k, v]) => (
                    <tr key={k}>
                      <td style={{ color: '#fbbf24', fontFamily: 'monospace' }}>{k}</td>
                      <td style={{ color: '#94a3b8' }}>{v}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* ── Audit Logs ── */}
        {tab === 'logs' && (
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>时间</th>
                  <th>管理员</th>
                  <th>操作</th>
                  <th>目标类型</th>
                  <th>目标 ID</th>
                </tr>
              </thead>
              <tbody>
                {auditLogs.map(log => (
                  <tr key={log.id}>
                    <td style={{ fontSize: 11 }}>{log.created_at?.slice(0, 19) || '-'}</td>
                    <td>{log.admin_id?.slice(0, 8)}</td>
                    <td><span className="admin-action-tag">{log.action}</span></td>
                    <td>{log.target_type}</td>
                    <td className="admin-cell-id">{log.target_id?.slice(0, 12)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
