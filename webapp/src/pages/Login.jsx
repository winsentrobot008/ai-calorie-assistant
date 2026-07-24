import React, { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import LoginButtons from '../components/LoginButtons'
import { useAuth } from '../store/auth'
import { isFacebookAvailable, getServerLoginUrl } from '../utils/facebookLogin'

/**
 * Login — stand-alone login/register page.
 *
 * Renders both email/password form and OAuth buttons.
 * Backed by the AuthContext store.
 *
 * Props:
 *   api      - FastAPI backend URL
 *   addLog   - logger callback
 *   onClose  - navigation callback after login
 */
export default function Login({ api, addLog, onClose }) {
  const { t } = useTranslation()
  const { login: authLogin } = useAuth()

  const [mode, setMode] = useState('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [name, setName] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  // ── Email/Password Auth ──
  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const endpoint = mode === 'login' ? '/user/login' : '/user/register'
      const params = new URLSearchParams({ email, password })
      if (mode === 'register') params.append('name', name || email.split('@')[0])

      const r = await fetch(`${api}/api/v1${endpoint}?${params}`, { method: 'POST' })
      if (r.ok) {
        const d = await r.json()
        authLogin(d.user_id, d.email, d.name)
        addLog(`[AUTH] 登录成功: ${d.email}`)
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

  // ── OAuth callback ──
  const handleOAuthLogin = (userId, email) => {
    authLogin(userId, email)
    addLog(`[AUTH] OAuth 登录成功: ${email}`)
    if (onClose) onClose()
  }

  // ── Anonymous ──
  const handleAnonymous = () => {
    const uid = `anon_${Date.now()}`
    authLogin(uid, '')
    addLog('[AUTH] 游客模式')
    if (onClose) onClose()
  }

  // ── Server-side Facebook redirect ──
  const handleFacebookRedirect = () => {
    const url = getServerLoginUrl(api)
    window.location.href = url
  }

  return (
    <div className="login-page">
      <div className="login-card">
        <h2 className="login-title">{t('login_title')}</h2>

        <form onSubmit={handleSubmit}>
          {error && <div className="login-error">{error}</div>}

          {mode === 'register' && (
            <div className="form-group">
              <label>{t('profile')}</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder={t('profile')}
                className="form-input"
              />
            </div>
          )}

          <div className="form-group">
            <label>{t('login_email')}</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder="your@email.com"
              className="form-input"
            />
          </div>

          <div className="form-group">
            <label>{t('login_password')}</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={4}
              placeholder="••••••"
              className="form-input"
            />
          </div>

          <button type="submit" className="btn-primary login-submit" disabled={loading}>
            {loading ? '...' : mode === 'login' ? t('login_btn') : t('login_register')}
          </button>
        </form>

        <div className="login-toggle">
          <button className="btn-link" onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError('') }}>
            {mode === 'login' ? t('login_register') : t('login_btn')}
          </button>
        </div>

        {/* OAuth Buttons (auto-detected, SDK-based) */}
        <LoginButtons
          api={api}
          onLogin={handleOAuthLogin}
          onError={setError}
          addLog={addLog}
        />

        {/* Facebook server redirect — 已临时禁用 (2026-07-24) */}
        {/* isFacebookAvailable() && (
          <button className="oauth-btn oauth-facebook" onClick={handleFacebookRedirect} style={{ marginTop: 8 }}>
            <span className="oauth-icon">f</span>
            <span>{t('oauth_facebook')} (安全授权)</span>
          </button>
        ) */}

        <div className="login-anonymous">
          <p>{t('login_anonymous_hint')}</p>
          <button className="btn-secondary login-anon-btn" onClick={handleAnonymous}>
            {t('login_continue_anon')}
          </button>
        </div>
      </div>
    </div>
  )
}
