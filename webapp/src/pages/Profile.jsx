import React, { useState, useEffect } from 'react'

export default function Profile({ api, addLog }) {
  const [userId] = useState(() => localStorage.getItem('calorie_user_id') || 'anonymous')
  const [name, setName] = useState('')
  const [goalType, setGoalType] = useState('maintain')
  const [dailyCalories, setDailyCalories] = useState(2000)
  const [dailyProtein, setDailyProtein] = useState(60)
  const [dailyFat, setDailyFat] = useState(65)
  const [dailyCarbs, setDailyCarbs] = useState(300)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  // Load profile on mount
  useEffect(() => {
    (async () => {
      try {
        const r = await fetch(`${api}/api/v1/user/profile?user_id=${userId}`)
        if (r.ok) {
          const data = await r.json()
          const u = data.user
          setName(u.name || '')
          setGoalType(u.goal_type || 'maintain')
          setDailyCalories(u.daily_calories || 2000)
          setDailyProtein(u.daily_protein || 60)
          setDailyFat(u.daily_fat || 65)
          setDailyCarbs(u.daily_carbs || 300)
        }
      } catch (e) {
        addLog(`[WARN] 加载用户资料失败: ${e.message}`)
      }
    })()
  }, [api, userId, addLog])

  const handleSave = async () => {
    setSaving(true)
    setSaved(false)
    try {
      const params = new URLSearchParams({
        user_id: userId,
        name,
        goal_type: goalType,
        daily_calories: dailyCalories.toString(),
        daily_protein: dailyProtein.toString(),
        daily_fat: dailyFat.toString(),
        daily_carbs: dailyCarbs.toString(),
      })
      const r = await fetch(`${api}/api/v1/user/profile?${params}`, { method: 'PUT' })
      if (r.ok) {
        setSaved(true)
        addLog('[SUCCESS] 目标已保存')
        setTimeout(() => setSaved(false), 2000)
      } else {
        addLog(`[Error] 保存失败: ${await r.text()}`)
      }
    } catch (e) {
      addLog(`[Error] ${e.message}`)
    }
    setSaving(false)
  }

  return (
    <div>
      {/* User Info */}
      <div className="card">
        <div className="card-title">用户信息</div>
        <div className="form-group">
          <label className="form-label">昵称</label>
          <input
            className="form-input"
            value={name}
            onChange={e => setName(e.target.value)}
            placeholder="你的昵称"
          />
        </div>
        <div className="form-group">
          <label className="form-label">用户 ID</label>
          <input className="form-input" value={userId} disabled style={{ opacity: 0.6 }} />
        </div>
      </div>

      {/* Daily Goals */}
      <div className="card">
        <div className="card-title">每日目标</div>

        <div className="form-group">
          <label className="form-label">目标类型</label>
          <div className="goal-type-row">
            {[
              { value: 'lose', label: '减脂' },
              { value: 'maintain', label: '维持' },
              { value: 'gain', label: '增肌' },
            ].map(opt => (
              <button
                key={opt.value}
                className={`goal-btn ${goalType === opt.value ? 'active' : ''}`}
                onClick={() => setGoalType(opt.value)}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        <div className="form-group">
          <label className="form-label">每日卡路里目标 (kcal)</label>
          <input
            className="form-input"
            type="number"
            value={dailyCalories}
            onChange={e => setDailyCalories(Number(e.target.value))}
            min={500}
            max={10000}
          />
        </div>

        <div className="macro-grid">
          <div className="form-group">
            <label className="form-label" style={{ color: '#34d399' }}>蛋白质 (g)</label>
            <input className="form-input" type="number" value={dailyProtein}
              onChange={e => setDailyProtein(Number(e.target.value))} min={0} />
          </div>
          <div className="form-group">
            <label className="form-label" style={{ color: '#60a5fa' }}>脂肪 (g)</label>
            <input className="form-input" type="number" value={dailyFat}
              onChange={e => setDailyFat(Number(e.target.value))} min={0} />
          </div>
          <div className="form-group">
            <label className="form-label" style={{ color: '#fbbf24' }}>碳水 (g)</label>
            <input className="form-input" type="number" value={dailyCarbs}
              onChange={e => setDailyCarbs(Number(e.target.value))} min={0} />
          </div>
        </div>

        <button className="submit-btn" onClick={handleSave} disabled={saving} style={{ marginTop: 12 }}>
          {saving ? <span className="spinner" /> : saved ? '✅ 已保存' : '💾 保存目标'}
        </button>
      </div>
    </div>
  )
}
