import React, { useState } from 'react'

const PLANS = {
  monthly: { price: 9.99, label: '月付', days: 30, popular: false },
  yearly: { price: 79.99, label: '年付', days: 365, popular: true },
  permanent: { price: 199.00, label: '永久买断', days: null, popular: false },
}

const PRO_FEATURES = [
  '无限次 AI 食物识别',
  '详细营养分析（蛋白质/脂肪/碳水）',
  '7 天饮食趋势图表',
  'AI 智能饮食建议',
  '无广告体验',
]

export default function BillingModal({ api, userId, billingStatus, onClose, onUpdate, addLog }) {
  const [activeTab, setActiveTab] = useState('subscription')
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')

  const isPremium = billingStatus?.is_premium
  const isPermanent = billingStatus?.is_permanent

  const handlePurchase = async (plan) => {
    setLoading(true)
    setMessage('')
    try {
      const endpoint = plan === 'permanent' ? '/billing/license' : '/billing/subscribe'
      const params = new URLSearchParams({
        user_id: userId || 'anonymous',
        plan,
        provider: 'stripe',
        provider_token: 'demo',
      })
      const r = await fetch(`${api}/api/v1${endpoint}?${params}`, { method: 'POST' })
      const d = await r.json()
      if (r.ok) {
        setMessage(`✅ ${d.message || '购买成功！'}`)
        addLog(`[BILLING] 购买成功: ${plan}`)
        if (onUpdate) onUpdate()
      } else {
        setMessage(`❌ ${d.detail || '购买失败'}`)
      }
    } catch (e) {
      setMessage(`❌ 网络错误: ${e.message}`)
    }
    setLoading(false)
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content billing-modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2>升级到 Pro</h2>
          <button className="modal-close" onClick={onClose}>&times;</button>
        </div>

        {/* Status Bar */}
        <div className="billing-status-bar">
          {isPermanent ? (
            <span className="badge badge-permanent">🌟 永久授权已激活 — 所有功能已解锁</span>
          ) : isPremium ? (
            <span className="badge badge-premium">⭐ Pro 会员活跃中 — 无限识别 + 去广告</span>
          ) : (
            <div className="free-tier-info">
              <span className="badge badge-free">
                免费用户 — 每日 {billingStatus?.daily_free_uses || 1} 次免费识别
              </span>
              <span className="free-remaining">
                今日剩余: <strong>{billingStatus?.remaining_daily_recognitions || 0}</strong> 次
                {/* 广告积分已临时禁用 (2026-07-24) */}
                {/* billingStatus?.ad_reward_credits > 0 && (
                  <span className="ad-credit-badge"> (含 {billingStatus.ad_reward_credits} 广告积分)</span>
                ) */}
              </span>
            </div>
          )}
        </div>

        {message && (
          <div className="billing-message">{message}</div>
        )}

        {/* Tabs */}
        <div className="billing-tabs">
          <button className={`billing-tab ${activeTab === 'subscription' ? 'active' : ''}`}
            onClick={() => setActiveTab('subscription')}>
            订阅方案
          </button>
          <button className={`billing-tab ${activeTab === 'license' ? 'active' : ''}`}
            onClick={() => setActiveTab('license')}>
            永久买断
          </button>
        </div>

        {activeTab === 'subscription' && (
          <div className="plan-grid">
            {['monthly', 'yearly'].map(plan => {
              const p = PLANS[plan]
              return (
                <div key={plan} className={`plan-card ${p.popular ? 'popular' : ''}`}>
                  {p.popular && <div className="plan-badge">最受欢迎</div>}
                  <div className="plan-name">{p.label}</div>
                  <div className="plan-price">
                    <span className="price">${p.price}</span>
                    <span className="period">/{plan === 'monthly' ? '月' : '年'}</span>
                  </div>
                  {plan === 'yearly' && (
                    <div className="plan-save">节省 ${(9.99 * 12 - 79.99).toFixed(2)}/年</div>
                  )}
                  <ul className="plan-features">
                    {PRO_FEATURES.map((f, i) => (
                      <li key={i}>{f}</li>
                    ))}
                  </ul>
                  <button className="btn-primary plan-btn"
                    onClick={() => handlePurchase(plan)}
                    disabled={loading || isPremium}>
                    {isPremium ? '已订阅' : loading ? '处理中...' : `订阅 ${p.label}`}
                  </button>
                </div>
              )
            })}
          </div>
        )}

        {activeTab === 'license' && (
          <div className="license-section">
            {isPermanent ? (
              <div className="license-activated">
                <div className="license-icon">🌟</div>
                <h3>永久授权已激活</h3>
                <p>感谢您的支持！所有 Pro 功能已永久解锁。</p>
              </div>
            ) : (
              <div className="plan-card permanent-card">
                <div className="plan-name">永久买断</div>
                <div className="plan-price">
                  <span className="price">${PLANS.permanent.price}</span>
                  <span className="period">一次付费，永久使用</span>
                </div>
                <ul className="plan-features">
                  <li>所有 Pro 功能永久解锁</li>
                  <li>无时间限制 · 无续费</li>
                  <li>无广告体验</li>
                  <li>优先体验新功能</li>
                  <li>终身免费更新</li>
                </ul>
                <div style={{ fontSize: 12, color: '#94a3b8', textAlign: 'center', margin: '4px 0 12px' }}>
                  相当于 {(PLANS.permanent.price / 12).toFixed(0)} 个月 Pro 费用，永久使用
                </div>
                <button className="btn-primary plan-btn btn-license"
                  onClick={() => handlePurchase('permanent')}
                  disabled={loading}>
                  {loading ? '处理中...' : `立即买断 $${PLANS.permanent.price}`}
                </button>
              </div>
            )}
          </div>
        )}

        <div className="billing-footer">
          <p>支付由 Stripe 安全处理。可随时取消订阅。</p>
        </div>
      </div>
    </div>
  )
}
