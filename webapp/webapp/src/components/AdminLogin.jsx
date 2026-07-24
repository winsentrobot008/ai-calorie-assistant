import React, { useState } from 'react'

const ADMIN_API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function AdminLogin({ onLogin }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleLogin = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const params = new URLSearchParams({ username, password })
      const r = await fetch(`${ADMIN_API}/api/v1/admin/login?${params}`, { method: 'POST' })
      const d = await r.json()
      if (r.ok) {
        onLogin({ adminId: d.admin_id, username: d.username, role: d.role })
      } else {
        setError(d.detail || '登录失败')
      }
    } catch (e) {
      setError('网络错误: ' + e.message)
    }
    setLoading(false)
  }

  return (
    <div className="admin-login-wrapper">
      <div className="admin-login-card">
        <h2>🔐 管理后台</h2>
        <p className="admin-login-hint">默认账号: admin / admin123</p>
        <form onSubmit={handleLogin}>
          <div className="form-group">
            <label className="form-label">用户名</label>
            <input className="form-input" value={username}
              onChange={e => setUsername(e.target.value)} placeholder="admin" />
          </div>
          <div className="form-group">
            <label className="form-label">密码</label>
            <input className="form-input" type="password" value={password}
              onChange={e => setPassword(e.target.value)} placeholder="admin123" />
          </div>
          {error && <p className="admin-login-error">{error}</p>}
          <button className="submit-btn" type="submit" disabled={loading}>
            {loading ? '登录中...' : '登录'}
          </button>
        </form>
      </div>
    </div>
  )
}
