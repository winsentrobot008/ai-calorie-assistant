import React, { useState, useRef } from 'react'

const MEAL_TYPES = [
  { value: 'breakfast', label: '🌅 早餐' },
  { value: 'lunch', label: '☀️ 午餐' },
  { value: 'dinner', label: '🌙 晚餐' },
  { value: 'snack', label: '🍿 加餐' },
]

export default function MealRecorder({ api, onSaved, addLog }) {
  const [mode, setMode] = useState('image') // image | text
  const [mealType, setMealType] = useState('breakfast')
  const [text, setText] = useState('')
  const [analyzing, setAnalyzing] = useState(false)
  const [result, setResult] = useState(null)
  const [previewUrl, setPreviewUrl] = useState(null) // image preview
  const [expandedIdx, setExpandedIdx] = useState(null) // for click-to-expand details
  const fileRef = useRef(null)

  // ── Image Upload + AI Recognition ──
  const handleImageUpload = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return

    // Show preview immediately
    const blobUrl = URL.createObjectURL(file)
    setPreviewUrl(blobUrl)

    setAnalyzing(true)
    setResult(null)
    addLog(`[Upload] 正在识别: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`)

    try {
      const fd = new FormData()
      fd.append('file', file)
      fd.append('meal_type', mealType)

      const r = await fetch(`${api}/api/v1/meals/analyze-image`, { method: 'POST', body: fd })
      if (r.ok) {
        const data = await r.json()
        setResult(data)
        if (data.model?.switched) {
          addLog(`[INFO] ${data.model.message}`)
        } else {
          addLog(`[AI] 识别到 ${data.count} 种食物`)
        }
        data.records?.forEach(rec => {
          addLog(`  🍽️ ${rec.food} — ${rec.calories} kcal (P${rec.protein_g}/F${rec.fat_g}/C${rec.carbs_g})`)
        })
        onSaved(data.model)
      } else {
        const err = await r.text()
        addLog(`[Error] ${err.slice(0, 100)}`)
      }
    } catch (e) {
      addLog(`[Error] ${e.message}`)
    }
    setAnalyzing(false)
    if (fileRef.current) fileRef.current.value = ''
  }

  // ── Text Input ──
  const handleTextSubmit = async () => {
    if (!text.trim()) return
    setAnalyzing(true)
    setResult(null)
    addLog(`[Text] 正在解析: "${text.slice(0, 50)}..."`)

    try {
      const fd = new FormData()
      fd.append('text', text.trim())
      fd.append('meal_type', mealType)

      const r = await fetch(`${api}/api/v1/meals/analyze-text`, { method: 'POST', body: fd })
      if (r.ok) {
        const data = await r.json()
        setResult(data)
        addLog(`[AI] 解析到 ${data.count} 种食物`)
        data.records?.forEach(rec => {
          addLog(`  🍽️ ${rec.food} (${rec.grams}g) — ${rec.calories} kcal`)
        })
        onSaved()
      } else {
        const err = await r.text()
        addLog(`[Error] ${err.slice(0, 100)}`)
      }
    } catch (e) {
      addLog(`[Error] ${e.message}`)
    }
    setAnalyzing(false)
  }

  return (
    <div>
      {/* Meal Type Selector */}
      <div className="card">
        <div className="card-title">选择餐次</div>
        <div className="meal-type-row">
          {MEAL_TYPES.map(mt => (
            <button
              key={mt.value}
              className={`meal-type-btn ${mealType === mt.value ? 'active' : ''}`}
              onClick={() => setMealType(mt.value)}
            >
              {mt.label}
            </button>
          ))}
        </div>
      </div>

      {/* Mode Toggle */}
      <div className="card">
        <div className="card-title">选择输入方式</div>
        <div className="tab-bar" style={{ margin: 0 }}>
          <button className={`tab ${mode === 'image' ? 'active' : ''}`} onClick={() => setMode('image')}>
            📷 拍照/上传
          </button>
          <button className={`tab ${mode === 'text' ? 'active' : ''}`} onClick={() => setMode('text')}>
            ✏️ 文字输入
          </button>
        </div>
      </div>

      {/* Image Mode */}
      {mode === 'image' && (
        <div className="card">
          <div className="card-title">上传食物照片</div>
          <div className="upload-area">
            <input
              ref={fileRef}
              type="file"
              accept="image/*"
              capture="environment"
              style={{ display: 'none' }}
              onChange={handleImageUpload}
            />
            <button className="upload-btn" onClick={() => fileRef.current?.click()} disabled={analyzing}>
              {analyzing ? <span className="spinner" /> : '📸 拍照或选择图片'}
            </button>
            {previewUrl && (
              <img src={previewUrl} alt="food preview" className="preview-thumb" />
            )}
          </div>
        </div>
      )}

      {/* Text Mode */}
      {mode === 'text' && (
        <div className="card">
          <div className="card-title">描述你吃了什么</div>
          <textarea
            className="text-input"
            placeholder='例如：中午吃了一碗米饭 + 一块鸡胸肉 + 一盘西兰花'
            value={text}
            onChange={e => setText(e.target.value)}
          />
          <button
            className="submit-btn"
            style={{ marginTop: 10 }}
            disabled={!text.trim() || analyzing}
            onClick={handleTextSubmit}
          >
            {analyzing ? <span className="spinner" /> : '🤖 AI 估算卡路里'}
          </button>
        </div>
      )}

      {/* Results */}
      {result && result.records?.length > 0 && (
        <div className="card">
          <div className="card-title">
            识别结果 · {MEAL_TYPES.find(mt => mt.value === mealType)?.label.replace(/^.{1,2}\s*/, '')}
            {result.records[0]?.source_model && (
              <span style={{ float: 'right', fontSize: 10, color: '#64748b' }}>
                {result.records[0].source_model}
              </span>
            )}
          </div>
          {result.records.map((rec, i) => (
            <div key={i}>
              <div
                className="food-item clickable"
                onClick={() => setExpandedIdx(expandedIdx === i ? null : i)}
              >
                <div style={{ flex: 1 }}>
                  <div className="food-name">{rec.food}</div>
                  {rec.food_en && (
                    <div className="food-name-en">{rec.food_en}</div>
                  )}
                  <div className="food-grams">{rec.grams}g</div>
                  {rec.confidence != null && (
                    <div className="confidence-row">
                      <div className="confidence-bar-bg">
                        <div
                          className="confidence-bar-fill"
                          style={{ width: `${Math.round(rec.confidence * 100)}%` }}
                        />
                      </div>
                      <span className="confidence-label">
                        {Math.round(rec.confidence * 100)}%
                      </span>
                    </div>
                  )}
                </div>
                <div className="food-nutrition">
                  <div className="food-cal">{rec.calories} kcal</div>
                  <div className="food-macro">
                    P{rec.protein_g} · F{rec.fat_g} · C{rec.carbs_g}
                  </div>
                </div>
              </div>
              {/* Expandable detail section */}
              {expandedIdx === i && (
                <div className="food-detail">
                  <div className="detail-grid">
                    <div className="detail-item">
                      <span className="detail-label">蛋白质</span>
                      <span className="detail-value">{rec.protein_g}g</span>
                    </div>
                    <div className="detail-item">
                      <span className="detail-label">脂肪</span>
                      <span className="detail-value">{rec.fat_g}g</span>
                    </div>
                    <div className="detail-item">
                      <span className="detail-label">碳水</span>
                      <span className="detail-value">{rec.carbs_g}g</span>
                    </div>
                    <div className="detail-item">
                      <span className="detail-label">份量</span>
                      <span className="detail-value">{rec.grams}g</span>
                    </div>
                    <div className="detail-item">
                      <span className="detail-label">模型</span>
                      <span className="detail-value">{rec.source_model || '-'}</span>
                    </div>
                    <div className="detail-item">
                      <span className="detail-label">语言</span>
                      <span className="detail-value">{rec.lang || 'zh'}</span>
                    </div>
                    {rec.food_en && (
                      <div className="detail-item" style={{ gridColumn: '1 / -1' }}>
                        <span className="detail-label">英文名</span>
                        <span className="detail-value">{rec.food_en}</span>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}
          <div className="food-item" style={{ borderBottom: 'none', marginTop: 4 }}>
            <div className="food-name">总计</div>
            <div className="food-nutrition">
              <div className="food-cal">
                {result.records.reduce((s, r) => s + r.calories, 0).toFixed(0)} kcal
              </div>
              <div className="food-macro">
                P{result.records.reduce((s, r) => s + r.protein_g, 0).toFixed(1)} ·
                F{result.records.reduce((s, r) => s + r.fat_g, 0).toFixed(1)} ·
                C{result.records.reduce((s, r) => s + r.carbs_g, 0).toFixed(1)}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
