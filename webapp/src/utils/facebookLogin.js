/**
 * facebookLogin.js — Frontend Facebook OAuth utility.
 *
 * Provides two login modes:
 *   1. Browser SDK login  (implicit token flow, used by LoginButtons)
 *   2. Server redirect login (authorization code flow, used by Login page)
 */

import { detectProviders } from './oauthDetect'

const PROVIDER_ID = 'facebook'
const REDIRECT_STORAGE_KEY = 'fb_oauth_state'

/**
 * Check if Facebook login is configured and available.
 */
export function isFacebookAvailable() {
  const { available } = detectProviders()
  return available.includes(PROVIDER_ID)
}

/**
 * Initialize Facebook SDK (async-safe, idempotent).
 * @param {string} appId - Facebook App ID
 * @param {Function} [callback] - Called after SDK is ready
 */
export function initFacebookSDK(appId, callback) {
  if (typeof window.FB !== 'undefined') {
    if (callback) callback()
    return
  }

  window.fbAsyncInit = function () {
    window.FB.init({ appId, cookie: true, xfbml: true, version: 'v18.0' })
    if (callback) callback()
  }

  if (!document.getElementById('facebook-jssdk')) {
    const js = document.createElement('script')
    js.id = 'facebook-jssdk'
    js.src = 'https://connect.facebook.net/zh_CN/sdk.js'
    const first = document.getElementsByTagName('script')[0]
    first.parentNode.insertBefore(js, first)
  }
}

/**
 * Login via Facebook SDK (implicit token flow).
 * @param {string} [scope] - Permissions scope
 * @returns {Promise<string>} Access token
 */
export function facebookLoginWithSDK(scope = 'public_profile,email') {
  return new Promise((resolve, reject) => {
    if (typeof window.FB === 'undefined') {
      reject(new Error('Facebook SDK not loaded'))
      return
    }
    window.FB.login(
      (response) => {
        if (response.authResponse) {
          resolve(response.authResponse.accessToken)
        } else {
          reject(new Error(response.status === 'not_authorized' ? 'Login cancelled' : 'Login failed'))
        }
      },
      { scope },
    )
  })
}

/**
 * Generate server-side redirect login URL.
 * Saves a CSRF state token in sessionStorage.
 * @param {string} api - Backend API base URL
 * @returns {string} Redirect URL to backend
 */
export function getServerLoginUrl(api) {
  const state = Math.random().toString(36).slice(2, 15)
  try { sessionStorage.setItem(REDIRECT_STORAGE_KEY, state) } catch (_) {}
  return `${api}/auth/facebook/login?state=${state}`
}

/**
 * Logout from Facebook (disconnect SDK).
 */
export function facebookLogout() {
  if (typeof window.FB !== 'undefined') {
    window.FB.logout()
  }
}

export default {
  isFacebookAvailable,
  initFacebookSDK,
  facebookLoginWithSDK,
  getServerLoginUrl,
  facebookLogout,
}
