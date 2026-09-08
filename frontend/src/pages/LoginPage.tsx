import { type FormEvent, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'

import { toApiError } from '../api/client'
import ErrorBanner from '../components/ErrorBanner'
import { useAuthStore } from '../store/authStore'
import { useCartStore } from '../store/cartStore'

/** Username + password sign-in. Merges any guest cart on success. */
export default function LoginPage() {
  const login = useAuthStore((state) => state.login)
  const loading = useAuthStore((state) => state.loading)
  const mergeGuestCart = useCartStore((state) => state.mergeGuestCart)
  const navigate = useNavigate()
  const location = useLocation()
  const redirectTo = (location.state as { from?: string } | null)?.from ?? '/'

  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    try {
      const user = await login(username.trim(), password)
      await mergeGuestCart()
      navigate(user.role === 'admin' && redirectTo === '/' ? '/admin' : redirectTo, {
        replace: true,
      })
    } catch (caught) {
      setError(toApiError(caught).message)
    }
  }

  return (
    <div className="mx-auto max-w-md">
      <h1 className="font-display text-3xl text-ink-900">Welcome back</h1>
      <p className="mt-1 text-sm text-ink-700">Sign in to see your cart and order history.</p>

      <form onSubmit={handleSubmit} className="card mt-6 space-y-4 p-6">
        <ErrorBanner message={error} onDismiss={() => setError(null)} />

        <div>
          <label className="label" htmlFor="username">
            Username
          </label>
          <input
            id="username"
            className="input"
            autoComplete="username"
            required
            value={username}
            onChange={(event) => setUsername(event.target.value)}
          />
        </div>

        <div>
          <label className="label" htmlFor="password">
            Password
          </label>
          <input
            id="password"
            type="password"
            className="input"
            autoComplete="current-password"
            required
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </div>

        <button type="submit" className="btn-primary w-full" disabled={loading}>
          {loading ? 'Signing in…' : 'Sign in'}
        </button>

        <p className="text-center text-sm text-ink-700">
          No account yet?{' '}
          <Link to="/register" className="font-semibold text-brand-700 hover:underline">
            Create one
          </Link>
        </p>
      </form>

      <div className="mt-4 rounded-lg border border-dashed border-ink-800/20 p-4 text-xs text-ink-700">
        <p className="font-semibold">Seeded demo logins</p>
        <p>admin / Admin123! — customer / Customer123!</p>
      </div>
    </div>
  )
}
