import { create } from 'zustand'

import { authApi, type RegisterPayload } from '../api/auth'
import { setSessionExpiredHandler, tokenStorage } from '../api/client'
import type { User } from '../types'

interface AuthState {
  user: User | null
  initialised: boolean
  loading: boolean
  login: (username: string, password: string) => Promise<User>
  register: (payload: RegisterPayload) => Promise<User>
  logout: () => Promise<void>
  bootstrap: () => Promise<void>
  isAdmin: () => boolean
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  initialised: false,
  loading: false,

  async login(username, password) {
    set({ loading: true })
    try {
      const response = await authApi.login(username, password)
      tokenStorage.set(response.access_token, response.refresh_token)
      set({ user: response.user, initialised: true })
      return response.user
    } finally {
      set({ loading: false })
    }
  },

  async register(payload) {
    set({ loading: true })
    try {
      const response = await authApi.register(payload)
      tokenStorage.set(response.access_token, response.refresh_token)
      set({ user: response.user, initialised: true })
      return response.user
    } finally {
      set({ loading: false })
    }
  },

  async logout() {
    const refresh = tokenStorage.refresh()
    if (refresh) {
      try {
        await authApi.logout(refresh)
      } catch {
        // A failed revoke must not trap the user in a signed-in state.
      }
    }
    tokenStorage.clear()
    set({ user: null })
  },

  async bootstrap() {
    if (get().initialised) return
    if (!tokenStorage.access()) {
      set({ initialised: true })
      return
    }
    try {
      const user = await authApi.me()
      set({ user, initialised: true })
    } catch {
      tokenStorage.clear()
      set({ user: null, initialised: true })
    }
  },

  isAdmin() {
    return get().user?.role === 'admin'
  },
}))

// When a refresh token finally fails, drop the session in the store too.
setSessionExpiredHandler(() => useAuthStore.setState({ user: null }))
