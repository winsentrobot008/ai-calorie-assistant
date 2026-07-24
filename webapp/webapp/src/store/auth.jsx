/**
 * auth.js — Centralized authentication store (React Context).
 *
 * Usage:
 *   <AuthProvider>
 *     <App />
 *   </AuthProvider>
 *
 *   const { user, login, logout, isLoggedIn } = useAuth()
 */

import React, { createContext, useContext, useState, useCallback, useEffect } from 'react'

const AuthContext = createContext(null)

/**
 * Load initial user state from localStorage.
 */
function loadUser() {
  const uid = localStorage.getItem('user_id')
  if (!uid) return null
  return {
    id: uid,
    email: localStorage.getItem('user_email') || '',
    name: localStorage.getItem('user_name') || '',
  }
}

/**
 * AuthProvider — wraps app to provide auth state globally.
 */
export function AuthProvider({ children }) {
  const [user, setUser] = useState(loadUser)
  const [loading, setLoading] = useState(false)

  const login = useCallback((userId, email, name) => {
    localStorage.setItem('user_id', userId)
    localStorage.setItem('user_email', email || '')
    if (name) localStorage.setItem('user_name', name)
    setUser({ id: userId, email: email || '', name: name || '' })
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('user_id')
    localStorage.removeItem('user_email')
    localStorage.removeItem('user_name')
    setUser(null)
  }, [])

  const isLoggedIn = !!user

  return (
    <AuthContext.Provider value={{ user, login, logout, isLoggedIn, loading, setLoading }}>
      {children}
    </AuthContext.Provider>
  )
}

/**
 * useAuth — hook to access authentication state.
 */
export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
