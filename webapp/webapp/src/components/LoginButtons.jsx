import React from 'react'
import { useTranslation } from 'react-i18next'
import { GoogleLogin, GoogleOAuthProvider } from '@react-oauth/google'
import { detectProviders } from '../utils/oauthDetect'

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || ''

/**
 * LoginButtons — 自动检测并渲染可用的 OAuth 登录按钮。
 *
 * Props:
 *   api          - FastAPI 后端地址
 *   onLogin(userId, email) - 登录成功回调
 *   onError(msg) - 错误回调
 *   addLog(msg)  - 日志回调
 */
export default function LoginButtons({ api, onLogin, onError, addLog }) {
  const { t } = useTranslation()
  const { available } = detectProviders()

  if (available.length === 0) return null

  const handleOAuth = async (provider, body) => {
    try {
      const r = await fetch(`${api}/api/v1/user/oauth/${provider}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (r.ok) {
        const d = await r.json()
        localStorage.setItem('user_id', d.user_id)
        localStorage.setItem('user_email', d.email)
        addLog(`[AUTH] ${provider} 登录成功: ${d.email}`)
        if (onLogin) onLogin(d.user_id, d.email)
      } else {
        const err = await r.json()
        if (onError) onError(err.detail || `${provider} 登录失败`)
      }
    } catch (e) {
      if (onError) onError(e.message)
    }
  }

  const handleGoogle = (resp) => {
    if (resp?.credential) handleOAuth('google', { token: resp.credential })
  }

  // Facebook 登录已临时禁用 (2026-07-24)
  // const handleFacebook = () => { ... }

  const handleApple = () => {
    if (typeof window.AppleID !== 'undefined') {
      window.AppleID.auth
        .signIn()
        .then((resp) => {
          if (resp?.authorization?.id_token) {
            handleOAuth('apple', {
              token: resp.authorization.id_token,
              user: resp.user || {},
            })
          }
        })
        .catch((err) => {
          if (onError) onError(err.message || 'Apple 登录失败')
        })
    } else if (onError) {
      onError('Apple SDK 未加载')
    }
  }

  return (
    <div className="oauth-section">
      <div className="oauth-divider"><span>{t('oauth_or')}</span></div>

      {available.includes('google') && (
        GOOGLE_CLIENT_ID ? (
          <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
            <div className="oauth-btn-row">
              <GoogleLogin
                onSuccess={handleGoogle}
                onError={() => onError && onError('Google 登录失败')}
                size="large"
                shape="rectangular"
                text="signin_with"
                theme="outline"
              />
            </div>
          </GoogleOAuthProvider>
        ) : (
          <button className="oauth-btn oauth-google" disabled>
            <span className="oauth-icon">G</span>
            <span>{t('oauth_google')}</span>
          </button>
        )
      )}

      {available.includes('apple') && (
        <button className="oauth-btn oauth-apple" onClick={handleApple}>
          <span className="oauth-icon">&#63743;</span>
          <span>{t('oauth_apple')}</span>
        </button>
      )}

      {/* Facebook 登录已临时禁用 (2026-07-24) */}
      {/* available.includes('facebook') && (
        <button className="oauth-btn oauth-facebook" onClick={handleFacebook}>
          <span className="oauth-icon">f</span>
          <span>{t('oauth_facebook')}</span>
        </button>
      ) */}
    </div>
  )
}
