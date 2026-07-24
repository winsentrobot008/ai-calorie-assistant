/**
 * oauthDetect — 自动检测可用的 OAuth 登录提供商
 *
 * 根据以下条件过滤：
 *   1. .env 环境变量中是否配置了对应 Client ID
 *   2. 设备平台 (iOS/Android/Web)
 *   3. 地区 (Facebook 在中国不可用)
 */

function getEnv(key) {
  return import.meta.env[key] || ''
}

function getPlatform() {
  const ua = navigator.userAgent || ''
  if (/iPad|iPhone|iPod/.test(ua)) return 'ios'
  if (/Android/.test(ua)) return 'android'
  if (/Mac OS/.test(ua)) return 'mac'
  if (/Windows/.test(ua)) return 'windows'
  if (/Linux/.test(ua)) return 'linux'
  return 'unknown'
}

function getRegion() {
  const lang = navigator.language || ''
  if (lang.startsWith('zh')) return 'cn'
  if (lang.startsWith('en')) return 'us'
  if (lang.startsWith('sv')) return 'se'
  if (lang.startsWith('ja')) return 'jp'
  return 'other'
}

/** 各提供商规则 */
const PROVIDERS = {
  google: {
    id: 'google',
    envVar: 'VITE_GOOGLE_CLIENT_ID',
    labelKey: 'oauth_google',
    platforms: ['ios', 'android', 'mac', 'windows', 'linux', 'unknown'],
    regions: ['cn', 'us', 'se', 'jp', 'other'],
  },
  apple: {
    id: 'apple',
    envVar: 'VITE_APPLE_CLIENT_ID',
    labelKey: 'oauth_apple',
    platforms: ['ios', 'mac'],
    regions: ['us', 'se', 'jp', 'other'],
  },
  facebook: {
    id: 'facebook',
    envVar: 'VITE_FACEBOOK_APP_ID',
    labelKey: 'oauth_facebook',
    platforms: ['android', 'windows', 'mac', 'linux', 'unknown'],
    regions: ['us', 'se', 'jp', 'other'],
  },
}

/**
 * 返回当前环境可用的 OAuth 提供商列表
 * @returns {{ available: string[], configured: string[], platform: string, region: string }}
 */
export function detectProviders() {
  const platform = getPlatform()
  const region = getRegion()

  const configured = []
  const available = []

  for (const cfg of Object.values(PROVIDERS)) {
    const envValue = getEnv(cfg.envVar)
    const isConfigured = !!envValue

    if (isConfigured) configured.push(cfg.id)

    if (
      isConfigured &&
      cfg.platforms.includes(platform) &&
      cfg.regions.includes(region)
    ) {
      available.push(cfg.id)
    }
  }

  return { available, configured, platform, region }
}

export { PROVIDERS }
