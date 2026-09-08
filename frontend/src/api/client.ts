import axios, { AxiosError, type AxiosInstance, type InternalAxiosRequestConfig } from 'axios'

import type { ApiError, TokenPair } from '../types'

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const ACCESS_KEY = 'toybox.access_token'
const REFRESH_KEY = 'toybox.refresh_token'

export const tokenStorage = {
  access: (): string | null => localStorage.getItem(ACCESS_KEY),
  refresh: (): string | null => localStorage.getItem(REFRESH_KEY),
  set(access: string, refresh: string) {
    localStorage.setItem(ACCESS_KEY, access)
    localStorage.setItem(REFRESH_KEY, refresh)
  },
  setAccess(access: string) {
    localStorage.setItem(ACCESS_KEY, access)
  },
  clear() {
    localStorage.removeItem(ACCESS_KEY)
    localStorage.removeItem(REFRESH_KEY)
  },
}

export const api: AxiosInstance = axios.create({
  baseURL: `${API_BASE_URL}/api`,
  headers: { 'Content-Type': 'application/json' },
  timeout: 20000,
})

api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = tokenStorage.access()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

/** Absolute URL for an image path returned by the backend. */
export function assetUrl(path: string | null | undefined): string {
  if (!path) return ''
  if (path.startsWith('http')) return path
  return `${API_BASE_URL}${path.startsWith('/') ? '' : '/'}${path}`
}

/** Pull the typed error body out of an Axios failure. */
export function toApiError(error: unknown): ApiError {
  const axiosError = error as AxiosError<{ error?: ApiError }>
  const payload = axiosError?.response?.data?.error
  if (payload) return payload
  if (axiosError?.response?.status === 401) {
    return { code: 'not_authenticated', message: 'Please sign in to continue.', field: null }
  }
  return {
    code: 'network_error',
    message: axiosError?.message || 'Something went wrong. Please try again.',
    field: null,
  }
}

let refreshing: Promise<string | null> | null = null
let onSessionExpired: (() => void) | null = null

/** Let the auth store clear itself when a refresh finally fails. */
export function setSessionExpiredHandler(handler: () => void) {
  onSessionExpired = handler
}

async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = tokenStorage.refresh()
  if (!refreshToken) return null
  try {
    const response = await axios.post<TokenPair>(`${API_BASE_URL}/api/auth/refresh`, {
      refresh_token: refreshToken,
    })
    tokenStorage.set(response.data.access_token, response.data.refresh_token)
    return response.data.access_token
  } catch {
    tokenStorage.clear()
    onSessionExpired?.()
    return null
  }
}

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as InternalAxiosRequestConfig & { _retried?: boolean }
    const isAuthCall = original?.url?.includes('/auth/login') || original?.url?.includes('/auth/refresh')

    if (error.response?.status === 401 && original && !original._retried && !isAuthCall) {
      original._retried = true
      refreshing = refreshing ?? refreshAccessToken()
      const token = await refreshing
      refreshing = null
      if (token) {
        original.headers.Authorization = `Bearer ${token}`
        return api(original)
      }
    }
    return Promise.reject(error)
  },
)
