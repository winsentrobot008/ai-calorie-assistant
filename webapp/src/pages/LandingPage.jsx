import React, { useState, useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import BillingModal from '../components/BillingModal'

const API = import.meta.env.VITE_API_URL || "/api"

const COMPARISON_ROWS = [
  { key: 'AI 食物拍照识别', freeKey: 'daily_1', proKey: 'unlimited' },
  { key: '营养数据分析', freeKey: 'basic', proKey: 'detailed' },
  { key: '7 天趋势图表', freeKey: 'basic_chart', proKey: 'full_chart' },
  { key: 'AI 饮食建议', freeKey: '✗', proKey: '✓' },
  { key: '广告', freeKey: 'has_ads', proKey: 'no_ads' },
  { key: '广告积分赚取', freeKey: '✓', proKey: '—' },
]

export default function LandingPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [showBilling, setShowBilling] = useState(false)
  const [billingStatus, setBillingStatus] = useState(null)
  const [loading, setLoading] = useState(false)
  const [mobileMenu, setMobileMenu] = useState(false)

  useEffect(() => {
    fetch(`${API}/api/v1/billing/status?user_id=${localStorage.getItem('user_id') || 'anonymous'}`)
      .then(r => r.json())
      .then(d => setBillingStatus(d))
      .catch(() => {})
  }, [])

  const features = useMemo(() => [
    { icon: '📸', title: t('landing_feature_vision'), desc: t('landing_feature_vision_desc') },
    { icon: '📊', title: t('landing_feature_nutrition'), desc: t('landing_feature_nutrition_desc') },
    { icon: '📈', title: t('landing_feature_trend'), desc: t('landing_feature_trend_desc') },
    { icon: '💡', title: t('landing_feature_ai'), desc: t('landing_feature_ai_desc') },
  ], [t])

  const plans = useMemo(() => [
    {
      tier: t('landing_free_tier'), price: '$0', period: '',
      features: [t('daily_1'), t('watch_ad'), t('basic'), t('basic_chart')],
      cta: t('landing_try_free'), popular: false, plan: 'free',
    },
    {
      tier: t('landing_pro_monthly'), price: '$9.99', period: `/${t('month')}`,
      features: [t('unlimited'), t('no_ads'), t('full_chart'), t('ai_suggestions'), t('detailed')],
      cta: t('landing_subscribe_monthly'), popular: false, plan: 'monthly',
    },
    {
      tier: t('landing_pro_yearly'), price: '$79.99', period: `/${t('year')}`,
      features: [t('all_pro'), t('save_money'), t('priority_queue'), t('dedicated_support')],
      cta: t('landing_subscribe_yearly'), popular: true, plan: 'yearly',
    },
    {
      tier: t('landing_permanent'), price: '$199', period: t('one_time'),
      features: [t('all_pro_unlocked'), t('no_time_limit'), t('free_updates'), t('early_access')],
      cta: t('landing_buy_permanent'), popular: false, plan: 'permanent',
    },
  ], [t])

  const handleTryNow = async () => {
    setLoading(true)
    try {
      await fetch(`${API}/api/v1/billing/status?user_id=${localStorage.getItem('user_id') || 'anonymous'}`)
      navigate('/app')
    } catch { navigate('/app') }
    setLoading(false)
  }

  const handlePricingClick = (plan) => {
    if (plan === 'free') handleTryNow()
    else setShowBilling(true)
  }

  const isPremium = billingStatus?.is_premium || billingStatus?.is_permanent
  const scrollTo = (id) => { document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' }); setMobileMenu(false) }

  return (
    <div className="landing-page">
      {/* ── Navbar ── */}
      <nav className="lp-nav">
        <div className="lp-nav-inner">
          <div className="lp-logo" onClick={() => scrollTo('hero')}>
            🥗 {t('app_title')}
          </div>
          <div className={`lp-nav-links ${mobileMenu ? 'open' : ''}`}>
            <button onClick={() => scrollTo('features')}>{t('landing_features_title')}</button>
            <button onClick={() => scrollTo('pricing')}>{t('landing_pricing_title')}</button>
            <button onClick={() => scrollTo('comparison')}>{t('landing_comparison_title')}</button>
            {billingStatus?.remaining_daily_recognitions > 0 && !isPremium && (
              <span className="lp-free-badge">{t('remaining_times', { count: billingStatus.remaining_daily_recognitions })}</span>
            )}
            <button className="btn-primary lp-nav-cta" onClick={handleTryNow} disabled={loading}>
              {loading ? '...' : t('landing_try_free')}
            </button>
          </div>
          <button className="lp-mobile-toggle" onClick={() => setMobileMenu(!mobileMenu)}>
            {mobileMenu ? '✕' : '☰'}
          </button>
        </div>
      </nav>

      {/* ── Hero ── */}
      <section id="hero" className="lp-hero">
        <div className="lp-hero-bg" />
        <div className="lp-hero-content">
          <h1 className="lp-hero-title">
            {t('landing_hero_title')}<br />
            <span className="lp-hero-highlight">{t('landing_hero_highlight')}</span>
          </h1>
          <p className="lp-hero-subtitle">{t('landing_hero_subtitle')}</p>
          <div className="lp-hero-actions">
            <button className="btn-primary btn-lg" onClick={handleTryNow} disabled={loading}>
              {loading ? '...' : t('landing_try_free')}
            </button>
            <button className="btn-secondary btn-lg" onClick={() => scrollTo('pricing')}>
              {t('landing_view_pricing')}
            </button>
          </div>
          <div className="lp-hero-stats">
            <div className="lp-stat">
              <span className="lp-stat-num">10,000+</span>
              <span className="lp-stat-label">{t('landing_active_users')}</span>
            </div>
            <div className="lp-stat">
              <span className="lp-stat-num">50,000+</span>
              <span className="lp-stat-label">{t('landing_food_records')}</span>
            </div>
            <div className="lp-stat">
              <span className="lp-stat-num">AI</span>
              <span className="lp-stat-label">{t('landing_ai_driven')}</span>
            </div>
          </div>
        </div>
      </section>

      {/* ── Features ── */}
      <section id="features" className="lp-section">
        <div className="lp-section-inner">
          <h2 className="lp-section-title">{t('landing_features_title')}</h2>
          <p className="lp-section-subtitle">{t('landing_features_subtitle')}</p>
          <div className="lp-features-grid">
            {features.map((f, i) => (
              <div key={i} className="lp-feature-card">
                <div className="lp-feature-icon">{f.icon}</div>
                <h3 className="lp-feature-title">{f.title}</h3>
                <p className="lp-feature-desc">{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Pricing ── */}
      <section id="pricing" className="lp-section lp-section-dark">
        <div className="lp-section-inner">
          <h2 className="lp-section-title">{t('landing_pricing_title')}</h2>
          <p className="lp-section-subtitle">{t('landing_pricing_subtitle')}</p>
          <div className="lp-pricing-grid">
            {plans.map((p, i) => (
              <div key={i} className={`lp-pricing-card ${p.popular ? 'popular' : ''} ${p.plan === 'free' ? 'free-tier' : ''}`}>
                {p.popular && <div className="lp-pricing-badge">{t('landing_most_popular')}</div>}
                {p.plan === 'permanent' && <div className="lp-pricing-badge lp-badge-permanent">{t('landing_best_value')}</div>}
                <div className="lp-pricing-tier">{p.tier}</div>
                <div className="lp-pricing-price">
                  <span className="lp-price">{p.price}</span>
                  <span className="lp-period">{p.period}</span>
                </div>
                <ul className="lp-pricing-features">
                  {p.features.map((f, j) => <li key={j}>{f}</li>)}
                </ul>
                <button className={`lp-pricing-btn ${p.popular ? 'btn-primary' : 'btn-outline'}`}
                  onClick={() => handlePricingClick(p.plan)} disabled={loading}>
                  {p.cta}
                </button>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Comparison Table ── */}
      <section id="comparison" className="lp-section">
        <div className="lp-section-inner">
          <h2 className="lp-section-title">{t('landing_comparison_title')}</h2>
          <p className="lp-section-subtitle">{t('landing_comparison_subtitle')}</p>
          <div className="lp-comparison-wrap">
            <table className="lp-comparison">
              <thead>
                <tr>
                  <th>{t('feature')}</th>
                  <th className="col-free">{t('landing_free_tier')}</th>
                  <th className="col-pro">Pro</th>
                </tr>
              </thead>
              <tbody>
                {COMPARISON_ROWS.map((row, i) => (
                  <tr key={i}>
                    <td>{row.key}</td>
                    <td className="col-free">{row.freeKey}</td>
                    <td className="col-pro">{row.proKey}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="lp-comparison-cta">
            <button className="btn-primary btn-lg" onClick={handleTryNow}>
              {t('landing_try_free')}
            </button>
          </div>
        </div>
      </section>

      {/* ── Testimonials ── */}
      <section className="lp-section lp-section-dark">
        <div className="lp-section-inner">
          <h2 className="lp-section-title">{t('testimonials')}</h2>
          <div className="lp-testimonials">
            {[1, 2, 3].map(i => (
              <div key={i} className="lp-testimonial-card">
                <div className="lp-testimonial-stars">{'★'.repeat(5)}</div>
                <p className="lp-testimonial-text">{t(`testimonial_${i}`)}</p>
                <div className="lp-testimonial-author">{t(`testimonial_author_${i}`)}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA ── */}
      <section className="lp-section lp-cta-section">
        <div className="lp-section-inner">
          <h2 className="lp-cta-title">{t('landing_cta_title')}</h2>
          <p className="lp-cta-subtitle">{t('landing_cta_subtitle')}</p>
          <button className="btn-primary btn-lg" onClick={handleTryNow} disabled={loading}>
            {loading ? '...' : `📸 ${t('landing_try_free')}`}
          </button>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="lp-footer">
        <div className="lp-footer-inner">
          <div className="lp-footer-col">
            <h4>🥗 {t('app_title')}</h4>
            <p>{t('landing_footer_desc')}</p>
          </div>
          <div className="lp-footer-col">
            <h4>{t('product')}</h4>
            <button onClick={() => scrollTo('features')}>{t('landing_features_title')}</button>
            <button onClick={() => scrollTo('pricing')}>{t('landing_pricing_title')}</button>
            <button onClick={() => scrollTo('comparison')}>{t('landing_comparison_title')}</button>
          </div>
          <div className="lp-footer-col">
            <h4>{t('support')}</h4>
            <button onClick={() => window.location.href = 'mailto:support@calorie-ai.com'}>{t('contact_us')}</button>
            <a href="#">{t('privacy')}</a>
            <a href="#">{t('terms')}</a>
          </div>
          <div className="lp-footer-col">
            <h4>{t('legal')}</h4>
            <a href="#">{t('privacy')}</a>
            <a href="#">{t('terms')}</a>
            <a href="#">{t('cookies')}</a>
          </div>
        </div>
        <div className="lp-footer-bottom">
          <p>&copy; {new Date().getFullYear()} {t('app_title')}. {t('all_rights')}</p>
        </div>
      </footer>

      <div className="lp-credits">Powered by AI Calorie Assistant v1.0</div>

      {showBilling && (
        <BillingModal
          api={API}
          userId={localStorage.getItem('user_id') || 'anonymous'}
          billingStatus={billingStatus}
          onClose={() => setShowBilling(false)}
          onUpdate={() => {
            fetch(`${API}/api/v1/billing/status?user_id=${localStorage.getItem('user_id') || 'anonymous'}`)
              .then(r => r.json())
              .then(d => setBillingStatus(d)).catch(() => {})
          }}
          addLog={(msg) => console.log(msg)}
        />
      )}
    </div>
  )
}
