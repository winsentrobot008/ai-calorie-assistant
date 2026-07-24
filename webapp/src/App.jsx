import React, { useState, useEffect, useCallback, Suspense } from 'react'
import { Routes, Route } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import './i18n'
import MealRecorder from './components/MealRecorder'
import DailyDashboard from './components/DailyDashboard'
import Profile from './pages/Profile'
import LandingPage from './pages/LandingPage'
import BillingModal from './components/BillingModal'
import LoginModal from './components/LoginModal'
import Login from './pages/Login'
// import AdBanner from './components/AdBanner'
import AdminLogin from './components/AdminLogin'
import AdminDashboard from './components/AdminDashboard'
import './App.css'

const API = import.meta.env.VITE_API_URL || "http://localhost:8000"
const USER_ID = localStorage.getItem('user_id') || 'anonymous'

export default function App() {
  const { t } = useTranslation()
  const [tab, setTab] = useState('record')
  const [adminSession, setAdminSession] = useState(() => {
    const saved = sessionStorage.getItem('admin_session')
    return saved ? JSON.parse(saved) : null
  })
  const [userGoal, setUserGoal] = useState({
    goal_type: 'maintain',
    daily_calories: 2000,
    daily_protein: 60,
    daily_fat: 65,
    daily_carbs: 300,
  })
  const [dailyStats, setDailyStats] = useState(null)
  const [suggestions, setSuggestions] = useState([])
  const [logs, setLogs] = useState(['[System] AI Calorie Assistant 已就绪'])
  const [billingStatus, setBillingStatus] = useState(null)
  const [showBilling, setShowBilling] = useState(false)
  const [showLogin, setShowLogin] = useState(false)
  const [adLoading, setAdLoading] = useState(false)
  const today = new Date().toISOString().slice(0, 10)

  const addLog = useCallback((msg) => {
    const t = `[${new Date().toLocaleTimeString('zh-CN', { hour12: false })}] ${msg}`
    setLogs(prev => [...prev.slice(-99), t])
  }, [])

  // Fetch billing status
  const refreshBilling = useCallback(async () => {
    try {
      const r = await fetch(`${API}/api/v1/billing/status?user_id=${USER_ID}`)
      if (r.ok) setBillingStatus(await r.json())
    } catch {}
  }, [])

  // 广告积分已临时禁用 (2026-07-24)
  // const handleWatchAd = useCallback(async () => { ... })

  // Fetch daily stats + suggestions
  const refreshStats = useCallback(async () => {
    try {
      const [sr, sugR] = await Promise.all([
        fetch(`${API}/api/v1/stats/daily?date=${today}`),
        fetch(`${API}/api/v1/stats/suggestions`),
      ])
      if (sr.ok) {
        const sd = await sr.json()
        setDailyStats(sd)
        if (sd.goals) setUserGoal(sd.goals)
      }
      if (sugR.ok) {
        const sugD = await sugR.json()
        setSuggestions(sugD.suggestions || [])
        if (sugD.model?.switched) {
          addLog(`[INFO] ${sugD.model.message}`)
        }
      }
    } catch (e) {
      addLog(`[WARN] 数据加载失败: ${e.message}`)
    }
  }, [today, addLog])

  useEffect(() => {
    refreshStats()
    refreshBilling()
  }, [refreshStats, refreshBilling])

  const handleMealSaved = useCallback((modelInfo) => {
    if (modelInfo?.switched) {
      addLog(`[INFO] ${t('model_switched')} (${modelInfo.provider})`)
    } else {
      addLog(`[SUCCESS] ${t('meal_saved')}`)
    }
    refreshStats()
  }, [addLog, refreshStats, t])

  const handleLogin = useCallback((userId, email) => {
    // Refresh billing status after login
    refreshBilling()
    refreshStats()
    if (email) {
      addLog(`[AUTH] 已登录: ${email}`)
    }
  }, [refreshBilling, refreshStats, addLog])

  const handleGoalUpdated = useCallback(() => {
    refreshStats()
  }, [refreshStats])

  const isPremium = billingStatus?.is_premium || billingStatus?.is_permanent

  // Handle admin login/logout
  const handleAdminLogin = (s) => {
    sessionStorage.setItem('admin_session', JSON.stringify(s))
    setAdminSession(s)
  }
  const handleAdminLogout = () => {
    sessionStorage.removeItem('admin_session')
    setAdminSession(null)
  }

  // If admin is logged in, show admin dashboard
  if (adminSession && !adminSession.pending) {
    return <AdminDashboard session={adminSession} onLogout={handleAdminLogout} />
  }

  return (
    <Suspense fallback={<div className="app-loading">Loading...</div>}>
    <Routes>
      {/* Landing Page */}
      <Route path="/" element={<LandingPage />} />

      {/* Login */}
      <Route path="/login" element={<Login api={API} addLog={addLog} />} />

      {/* Main App */}
      <Route path="/app" element={
        <div className="app">
          {/* Header */}
          <header className="header">
            <div className="header-left">
              <span className="logo"
                onDoubleClick={() => setAdminSession({ pending: true })}
                onClick={() => window.location.href = '/'}
                style={{ cursor: 'pointer' }}>
                🥗 {t('app_title')}
              </span>
              <span className="goal-badge">{t(userGoal.goal_type === 'lose' ? 'goal_lose' : userGoal.goal_type === 'gain' ? 'goal_gain' : 'goal_maintain')}</span>
              {billingStatus?.is_permanent && <span className="badge badge-permanent-sm">{t('permanent_badge')}</span>}
              {billingStatus?.is_premium && <span className="badge badge-premium-sm">{t('pro_badge')}</span>}
            </div>
            <div className="header-right">
              {!isPremium && billingStatus && (
                <span className="remaining-badge">
                  {t('remaining_times', { count: billingStatus.remaining_daily_recognitions || 0 })}
                </span>
              )}
              {!isPremium && billingStatus && (billingStatus.remaining_daily_recognitions || 0) <= 0 && (
                <button className="btn-ad-reward" onClick={handleWatchAd} disabled={adLoading}>
                  {adLoading ? '⏳' : `📺 ${t('watch_ad')}`}
                </button>
              )}
              <span className="daily-target">{t('daily_target', { calories: userGoal.daily_calories })}</span>
              <button className="btn-login" onClick={() => setShowLogin(true)}>
                {localStorage.getItem('user_email') ? localStorage.getItem('user_email').split('@')[0] : t('login_btn')}
              </button>
              {!isPremium && (
                <button className="btn-upgrade" onClick={() => setShowBilling(true)}>
                  {t('upgrade_pro')}
                </button>
              )}
            </div>
          </header>

          {/* Tab Bar */}
          <nav className="tab-bar">
            <button className={`tab ${tab === 'record' ? 'active' : ''}`} onClick={() => setTab('record')}>
              📝 {t('record_diet')}
            </button>
            <button className={`tab ${tab === 'dashboard' ? 'active' : ''}`} onClick={() => setTab('dashboard')}>
              📊 {t('daily_stats')}
            </button>
            <button className={`tab ${tab === 'profile' ? 'active' : ''}`} onClick={() => setTab('profile')}>
              👤 {t('profile')}
            </button>
          </nav>

          {/* Content */}
          <main className="content">
            {adminSession?.pending ? (
              <AdminLogin onLogin={handleAdminLogin} />
            ) : tab === 'record' ? (
              <>
                <MealRecorder api={API} onSaved={handleMealSaved} addLog={addLog} />
                {/* AdBanner 已临时禁用 (2026-07-24) */}
                {/* !isPremium && <AdBanner api={API} userId={USER_ID} adType="banner" addLog={addLog} /> */}
              </>
            ) : tab === 'dashboard' ? (
              <DailyDashboard
                stats={dailyStats}
                suggestions={suggestions}
                goal={userGoal}
                today={today}
                addLog={addLog}
                api={API}
              />
            ) : (
              <Profile api={API} addLog={addLog} onGoalUpdated={handleGoalUpdated} />
            )}
          </main>

          {/* Terminal Logs */}
          <footer className="footer">
            <div className="log-bar">
              <span className="log-label">📋 日志</span>
              <div className="log-scroll">
                {logs.map((l, i) => (
                  <div key={i} className="log-line">{l}</div>
                ))}
              </div>
            </div>
          </footer>

          {/* Login Modal */}
          {showLogin && (
            <LoginModal
              api={API}
              onLogin={handleLogin}
              onClose={() => setShowLogin(false)}
              addLog={addLog}
            />
          )}

          {/* Billing Modal */}
          {showBilling && (
            <BillingModal
              api={API}
              userId={USER_ID}
              billingStatus={billingStatus}
              onClose={() => setShowBilling(false)}
              onUpdate={() => { refreshBilling(); addLog('[BILLING] 状态已更新') }}
              addLog={addLog}
            />
          )}
        </div>
      } />
    </Routes>
    </Suspense>
  )
}
