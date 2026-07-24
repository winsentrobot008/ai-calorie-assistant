/**
 * i18n Internationalization Setup
 *
 * Detects browser language on load and provides `t()` function.
 * Follows system language: zh / sv / en (fallback).
 */
import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

import zh from './zh.json'
import en from './en.json'
import sv from './sv.json'

const resources = { zh: { translation: zh }, en: { translation: en }, sv: { translation: sv } }

// Detect system language
let detectedLang = 'en'
if (typeof navigator !== 'undefined') {
  const raw = navigator.language || navigator.userLanguage || 'en'
  if (raw.startsWith('zh')) detectedLang = 'zh'
  else if (raw.startsWith('sv')) detectedLang = 'sv'
  else detectedLang = 'en'
}

i18n.use(initReactI18next).init({
  resources,
  lng: detectedLang,
  fallbackLng: 'en',
  interpolation: { escapeValue: false },
  keySeparator: false,
})

export default i18n
