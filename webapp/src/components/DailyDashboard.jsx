import React, { useState, useEffect } from 'react'
import TrendChart from './TrendChart'

function StatBar({ label, current, target, unit, color }) {
  const pct = target > 0 ? Math.min((current / target) * 100, 100) : 0
  const diff = current - target
  return (
    <div className="stat-row">
      <span className="stat-label">{label}</span>
      <div className="stat-bar-bg">
        <div className="stat-bar-fill" style={{ width: `${pct}%`, background: color }} />
      </div>
      <span className="stat-value" style={{ color: diff > 0 ? '#fbbf24' : '#94a3b8' }}>
        {current.toFixed(0)}/{target.toFixed(0)} {unit}
      </span>
    </div>
  )
}

function CalCircle({ calories, target }) {
  const pct = target > 0 ? Math.min((calories / target) * 100, 100) : 0
  const r = 54; const circ = 2 * Math.PI * r
  const offset = circ - (pct / 100) * circ
  const diff = calories - target
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '8px 0' }}>
      <svg width="140" height="140" viewBox="0 0 120 120">
        <circle cx="60" cy="60" r={r} fill="none" stroke="#1e293b" strokeWidth="8" />
        <circle cx="60" cy="60" r={r} fill="none" stroke="url(#calGrad)" strokeWidth="8"
          strokeDasharray={circ} strokeDashoffset={offset} strokeLinecap="round"
          transform="rotate(-90 60 60)" style={{ transition: 'stroke-dashoffset .8s' }} />
        <defs>
          <linearGradient id="calGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#f59e0b" />
            <stop offset="100%" stopColor="#ef4444" />
          </linearGradient>
        </defs>
        <text x="60" y="52" textAnchor="middle" fill="#f1f5f9" fontSize="22" fontWeight="700">
          {calories.toFixed(0)}
        </text>
        <text x="60" y="70" textAnchor="middle" fill="#64748b" fontSize="11">
          / {target.toFixed(0)} kcal
        </text>
      </svg>
      {diff > 0 ? (
        <span style={{ fontSize: 12, color: '#fbbf24', marginTop: 4 }}>超标 {diff.toFixed(0)} kcal</span>
      ) : (
        <span style={{ fontSize: 12, color: '#34d399', marginTop: 4 }}>还可摄入 {Math.abs(diff).toFixed(0)} kcal</span>
      )}
    </div>
  )
}

/* Meal-type distribution donut chart */
function MealDistribution({ trendDays }) {
  if (!trendDays || trendDays.length === 0) return null

  const today = trendDays[trendDays.length - 1]
  const mt = today.meal_types
  if (!mt) return null

  const total = mt.breakfast + mt.lunch + mt.dinner + mt.snack
  if (total === 0) return null

  const items = [
    { label: '早餐', key: 'breakfast', cal: mt.breakfast, color: '#f59e0b' },
    { label: '午餐', key: 'lunch', cal: mt.lunch, color: '#34d399' },
    { label: '晚餐', key: 'dinner', cal: mt.dinner, color: '#60a5fa' },
    { label: '加餐', key: 'snack', cal: mt.snack, color: '#a78bfa' },
  ].filter(i => i.cal > 0)

  if (items.length === 0) return null

  const r = 40
  const circ = 2 * Math.PI * r
  let offset = 0

  return (
    <div className="card" style={{ marginTop: 0 }}>
      <div className="card-title">🥗 今日饮食分布</div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 16, justifyContent: 'center' }}>
        <svg width="110" height="110" viewBox="0 0 100 100">
          {items.map((item, i) => {
            const pct = item.cal / total
            const segLen = pct * circ
            const gap = 2
            const dashArray = `${segLen - gap} ${circ - segLen + gap}`
            const seg = (
              <circle key={i} cx="50" cy="50" r={r} fill="none"
                stroke={item.color} strokeWidth="14"
                strokeDasharray={dashArray}
                strokeDashoffset={-offset}
                transform="rotate(-90 50 50)"
                style={{ transition: 'stroke-dashoffset .6s' }}
              />
            )
            offset += segLen
            return seg
          })}
          <text x="50" y="46" textAnchor="middle" fill="#f1f5f9" fontSize="16" fontWeight="700">
            {total.toFixed(0)}
          </text>
          <text x="50" y="60" textAnchor="middle" fill="#64748b" fontSize="8">kcal</text>
        </svg>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          {items.map((item, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: item.color, display: 'inline-block' }} />
              <span style={{ fontSize: 11, color: '#94a3b8' }}>{item.label}</span>
              <span style={{ fontSize: 11, color: '#f1f5f9', fontWeight: 600 }}>{item.cal.toFixed(0)}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default function DailyDashboard({ stats, suggestions, goal, today, addLog, api }) {
  const [insightSuggestions, setInsightSuggestions] = useState([])
  const [trendDays, setTrendDays] = useState([])
  const [loadingInsight, setLoadingInsight] = useState(false)

  // Fetch 7-day insight + trend with meal types
  useEffect(() => {
    (async () => {
      setLoadingInsight(true)
      try {
        const [sugR, trendR] = await Promise.all([
          fetch(`${api}/api/v1/insight/suggestions`),
          fetch(`${api}/api/v1/insight/trend?period=weekly`),
        ])
        if (sugR.ok) {
          const d = await sugR.json()
          setInsightSuggestions(d.suggestions || [])
        }
        if (trendR.ok) {
          const d = await trendR.json()
          setTrendDays(d.days || [])
        }
      } catch (e) {
        addLog(`[WARN] 洞察数据加载失败: ${e.message}`)
      }
      setLoadingInsight(false)
    })()
  }, [api, addLog])

  if (!stats || stats.status !== 'ok') {
    return (
      <div className="card" style={{ textAlign: 'center', padding: 40 }}>
        <span style={{ fontSize: 40 }}>📊</span>
        <p style={{ marginTop: 12, color: '#64748b', fontSize: 13 }}>还没有饮食记录，先去记录一餐吧！</p>
      </div>
    )
  }

  const s = stats.stats
  const g = goal || {}

  return (
    <div>
      {/* Date */}
      <div className="card" style={{ padding: '10px 16px', textAlign: 'center' }}>
        <span style={{ fontSize: 12, color: '#64748b' }}>{today}</span>
      </div>

      {/* Calorie Ring */}
      <div className="card" style={{ display: 'flex', justifyContent: 'center' }}>
        <CalCircle calories={s.calories} target={g.daily_calories || 2000} />
      </div>

      {/* Macro Breakdown */}
      <div className="card">
        <div className="card-title">营养明细</div>
        <StatBar label="蛋白质" current={s.protein_g} target={g.daily_protein || 60} unit="g" color="#34d399" />
        <StatBar label="脂肪"   current={s.fat_g} target={g.daily_fat || 65} unit="g" color="#60a5fa" />
        <StatBar label="碳水"   current={s.carbs_g} target={g.daily_carbs || 300} unit="g" color="#fbbf24" />
        {s.meal_count > 0 && (
          <div style={{ textAlign: 'center', marginTop: 8, fontSize: 11, color: '#64748b' }}>
            共 {s.meal_count} 条饮食记录
          </div>
        )}
      </div>

      {/* Meal-type Distribution (today) */}
      <MealDistribution trendDays={trendDays} />

      {/* Trend Chart */}
      <TrendChart api={api} addLog={addLog} insightTrendDays={trendDays} />

      {/* AI Suggestions (7-day enhanced) */}
      {(insightSuggestions.length > 0 || suggestions.length > 0) && (
        <div className="card">
          <div className="card-title">
            💡 AI 饮食建议
            {insightSuggestions.length > 0 && (
              <span style={{ float: 'right', fontSize: 10, color: '#64748b' }}>
                基于7天数据
              </span>
            )}
          </div>
          {(insightSuggestions.length > 0 ? insightSuggestions : suggestions).slice(0, 4).map((sg, i) => (
            <div key={i} className="suggestion-card">
              <span className="suggestion-icon">{sg.icon || '💡'}</span>
              <div>
                <div className="suggestion-title">{sg.title || ''}</div>
                <div className="suggestion-detail">{sg.detail || ''}</div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
