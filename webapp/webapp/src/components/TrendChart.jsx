import React, { useState, useEffect, useRef } from 'react'

const W = 400
const H = 180
const PAD = { top: 20, right: 16, bottom: 28, left: 44 }

export default function TrendChart({ api, addLog, insightTrendDays }) {
  const [period, setPeriod] = useState('weekly') // weekly | monthly
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(false)
  const [tooltip, setTooltip] = useState(null)
  const containerRef = useRef(null)

  useEffect(() => {
    // If insightTrendDays is available and period matches, use it directly
    if (insightTrendDays && insightTrendDays.length > 0 && period === 'weekly') {
      setData(insightTrendDays)
      return
    }
    (async () => {
      setLoading(true)
      try {
        const r = await fetch(`${api}/api/v1/insight/trend?period=${period}`)
        if (r.ok) {
          const d = await r.json()
          setData(d.days || [])
        }
      } catch (e) {
        addLog(`[WARN] 趋势数据加载失败: ${e.message}`)
      }
      setLoading(false)
    })()
  }, [api, period, addLog, insightTrendDays])

  if (loading) {
    return <div className="card" style={{ textAlign: 'center', padding: 24 }}>
      <span className="spinner" />
    </div>
  }

  if (!data.length) {
    return (
      <div className="card">
        <div className="card-title">📈 卡路里趋势</div>
        <div className="trend-toggle">
          <button className={`trend-btn ${period === 'weekly' ? 'active' : ''}`} onClick={() => setPeriod('weekly')}>本周</button>
          <button className={`trend-btn ${period === 'monthly' ? 'active' : ''}`} onClick={() => setPeriod('monthly')}>本月</button>
        </div>
        <p style={{ textAlign: 'center', color: '#64748b', fontSize: 12, padding: 20 }}>
          暂无趋势数据，开始记录饮食吧！
        </p>
      </div>
    )
  }

  const maxCal = Math.max(...data.map(d => d.calories || 0), ...data.map(d => d.goal_calories || 0), 100)
  const chartW = W - PAD.left - PAD.right
  const chartH = H - PAD.top - PAD.bottom
  const stepX = chartW / Math.max(data.length - 1, 1)

  const getX = (i) => PAD.left + i * stepX
  const getY = (v) => PAD.top + chartH - (v / maxCal) * chartH

  const calPoints = data.map((d, i) => `${getX(i)},${getY(d.calories)}`).join(' ')
  const goalY = getY(data[0]?.goal_calories || 2000)

  return (
    <div className="card" style={{ position: 'relative' }} ref={containerRef}>
      <div className="card-title">📈 卡路里趋势</div>

      <div className="trend-toggle">
        <button className={`trend-btn ${period === 'weekly' ? 'active' : ''}`} onClick={() => setPeriod('weekly')}>本周</button>
        <button className={`trend-btn ${period === 'monthly' ? 'active' : ''}`} onClick={() => setPeriod('monthly')}>本月</button>
      </div>

      <div className="trend-container">
        <svg viewBox={`0 0 ${W} ${H}`} className="trend-chart-svg"
          onMouseLeave={() => setTooltip(null)}>

          {/* Grid lines */}
          {[0, 0.25, 0.5, 0.75, 1].map((r, i) => {
            const y = PAD.top + chartH * (1 - r)
            const val = Math.round(maxCal * r)
            return (
              <g key={i}>
                <line x1={PAD.left} y1={y} x2={W - PAD.right} y2={y} stroke="#1e293b" strokeWidth="1" />
                <text x={PAD.left - 6} y={y + 3} textAnchor="end" fill="#64748b" fontSize="9">{val}</text>
              </g>
            )
          })}

          {/* Goal line */}
          {data[0]?.goal_calories > 0 && (
            <line x1={PAD.left} y1={goalY} x2={W - PAD.right} y2={goalY}
              stroke="#f59e0b44" strokeWidth="1" strokeDasharray="4,3" />
          )}

          {/* Area fill */}
          <path d={`M${getX(0)},${PAD.top + chartH} L${calPoints} L${getX(data.length - 1)},${PAD.top + chartH} Z`}
            fill="url(#trendGrad)" opacity="0.15" />

          <defs>
            <linearGradient id="trendGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#60a5fa" />
              <stop offset="100%" stopColor="#60a5fa00" />
            </linearGradient>
          </defs>

          {/* Line */}
          <polyline points={calPoints} fill="none" stroke="#60a5fa" strokeWidth="2" strokeLinejoin="round" />

          {/* Dots */}
          {data.map((d, i) => {
            const cx = getX(i)
            const cy = getY(d.calories)
            return (
              <circle key={i} cx={cx} cy={cy} r="3.5" fill="#60a5fa" stroke="#12141d" strokeWidth="1.5"
                style={{ cursor: 'pointer' }}
                onMouseEnter={() => setTooltip({ x: cx, y: cy, data: d })}
              />
            )
          })}

          {/* X-axis labels */}
          {data.map((d, i) => {
            const x = getX(i)
            const label = period === 'weekly'
              ? (i === 0 ? '6天前' : i === data.length - 1 ? '今天' : d.weekday)
              : d.date.slice(5)
            if (period === 'monthly' && i % 5 !== 0 && i !== data.length - 1) return null
            return (
              <text key={i} x={x} y={H - 4} textAnchor="middle" fill="#64748b" fontSize="8">
                {label}
              </text>
            )
          })}
        </svg>

        {/* Tooltip */}
        {tooltip && (
          <div className="trend-tooltip"
            style={{
              left: Math.min(tooltip.x - 40, W - 120),
              top: Math.max(tooltip.y - 60, 0),
            }}>
            <div style={{ fontWeight: 600, fontSize: 13 }}>{tooltip.data.calories} kcal</div>
            <div style={{ fontSize: 10, color: '#94a3b8' }}>{tooltip.data.date}</div>
            <div style={{ fontSize: 10, color: '#94a3b8' }}>
              P{tooltip.data.protein_g} · F{tooltip.data.fat_g} · C{tooltip.data.carbs_g}
            </div>
            {tooltip.data.meal_types && (
              <div style={{ fontSize: 10, color: '#94a3b8', marginTop: 2 }}>
                早{tooltip.data.meal_types.breakfast} 午{tooltip.data.meal_types.lunch}
                晚{tooltip.data.meal_types.dinner} 加{tooltip.data.meal_types.snack}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
