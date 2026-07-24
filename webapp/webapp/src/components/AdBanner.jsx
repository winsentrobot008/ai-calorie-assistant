import React, { useEffect, useRef } from 'react'

export default function AdBanner({ api, userId, adType = 'banner', addLog }) {
  const loggedRef = useRef(false)

  useEffect(() => {
    if (loggedRef.current) return
    loggedRef.current = true

    // Log impression
    const params = new URLSearchParams({
      user_id: userId || 'anonymous',
      ad_type: adType,
      action: 'impression',
      page_url: window.location.href,
    })
    fetch(`${api}/api/v1/ads/log?${params}`, { method: 'POST' }).catch(() => {})
  }, [api, userId, adType])

  const handleClick = () => {
    const params = new URLSearchParams({
      user_id: userId || 'anonymous',
      ad_type: adType,
      action: 'click',
      page_url: window.location.href,
    })
    fetch(`${api}/api/v1/ads/log?${params}`, { method: 'POST' }).catch(() => {})
  }

  const isBanner = adType === 'banner'

  return (
    <div className={`ad-container ${isBanner ? 'ad-banner' : 'ad-sidebar'}`} onClick={handleClick}>
      {isBanner ? (
        <div className="ad-placeholder">
          <span className="ad-label">广告</span>
          <span className="ad-text">AI 卡路里助手 Pro — 无限制识别，仅 ${/*monthly*/}9.99/月</span>
          <a href="#upgrade" className="ad-cta">升级</a>
        </div>
      ) : (
        <div className="ad-placeholder sidebar-ad">
          <span className="ad-label">赞助</span>
          <p style={{ fontSize: 12, color: '#94a3b8', margin: '4px 0' }}>
            去广告 + 无限识别
          </p>
          <a href="#upgrade" className="ad-cta" style={{ fontSize: 11 }}>升级 Pro</a>
        </div>
      )}
    </div>
  )
}
