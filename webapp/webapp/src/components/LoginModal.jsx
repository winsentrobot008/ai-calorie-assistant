import React, { useState } from 'react'
import { useTranslation } from 'react-i18next'
import LoginButtons from './LoginButtons'

export default function LoginModal({ api, onLogin, onClose, addLog }) {
  const { t } = useTranslation()
  const [mode, setMode] = useState('login')  // login | register
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    try {
      const endpoint = mode === 'login' ? '/user/login' : '/user/register'
      const params = new URLSearchParams({ email, password })
      if (mode === 'register') params.append('name', name || email.split('@')[0])

      const r = await fetch(`${api}/api/v1${endpoint}?${params}`, {
        method: mode === 'login' ? 'POST' : 'POST',
      })

      if (r.ok) {
        const d = await r.json()
        localStorage.setItem('user_id', d.user_id)
        localStorage.setItem('user_email', d.email)
        addLog(`[AUTH] 登录成功: ${d.email}`)
        if (onLogin) onLogin(d.user_id, d.email)
        if (onClose) onClose()
      } else {
        const err = await r.json()
        setError(err.detail || t('login_error'))
      }
    } catch (e) {
      setError(e.message)
    }
    setLoading(false)
  }

  const handleAnonymous = () => {
    localStorage.setItem('user_id', `anon_${Date.now()}`)
    addLog('[AUTH] 游客模式继续')
    if (onLogin) onLogin(localStorage.getItem('user_id'), '')
    if (onClose) onClose()
  }

  const handleOAuthLogin = (userId, email) => {
    if (onLogin) onLogin(userId, email)
    if (onClose) onClose()
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content login-modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2>{t('login_title')}</h2>
          <button className="modal-close" onClick={onClose}>&times;</button>
        </div>

        <form onSubmit={handleSubmit} className="login-form">
          {error && <div className="login-error">{error}</div>}

          {mode === 'register' && (
            <div className="form-group">
              <label>{t('profile')}</label>
              <input type="text" value={name} onChange={e => setName(e.target.value)}
                placeholder={t('profile')} className="form-input" />
            </div>
          )}

          <div className="form-group">
            <label>{t('login_email')}</label>
            <input type="email" value={email} onChange={e => setEmail(e.target.value)}
              required placeholder="your@email.com" className="form-input" />
          </div>

          <div className="form-group">
            <label>{t('login_password')}</label>
            <input type="password" value={password} onChange={e => setPassword(e.target.value)}
              required minLength={4} placeholder="••••••" className="form-input" />
          </div>

          <button type="submit" className="btn-primary login-submit" disabled={loading}>
            {loading ? '...' : (mode === 'login' ? t('login_btn') : t('login_register'))}
          </button>
        </form>

        <div className="login-toggle">
          <button className="btn-link" onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError('') }}>
            {mode === 'login' ? t('login_register') : t('login_btn')}
          </button>
        </div>

        {/* OAuth Section — auto-detected providers */}
        <LoginButtons
          api={api}
          onLogin={handleOAuthLogin}
          onError={setError}
          addLog={addLog}
        />

        <div className="login-anonymous">
          <p>{t('login_anonymous_hint')}</p>
          <button className="btn-secondary login-anon-btn" onClick={handleAnonymous}>
            {t('login_continue_anon')}
          </button>
        </div>

        {/* Logout button - shown when user is logged in via email */}
        {localStorage.getItem('user_email') && (
          <div className="login-logout">
            <button className="btn-link logout-btn" onClick={() => {
              localStorage.removeItem('user_id')
              localStorage.removeItem('user_email')
              addLog('[AUTH] 已退出登录')
              if (onLogin) onLogin('anonymous', '')
              if (onClose) onClose()
            }}>
              {t('logout')}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
