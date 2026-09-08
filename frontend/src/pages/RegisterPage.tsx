import { type FormEvent, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { toApiError } from '../api/client'
import ErrorBanner from '../components/ErrorBanner'
import { useAuthStore } from '../store/authStore'
import { useCartStore } from '../store/cartStore'

/** Create a customer account. */
export default function RegisterPage() {
  const register = useAuthStore((state) => state.register)
  const loading = useAuthStore((state) => state.loading)
  const mergeGuestCart = useCartStore((state) => state.mergeGuestCart)
  const navigate = useNavigate()

  const [form, setForm] = useState({ username: '', email: '', full_name: '', password: '' })
  const [error, setError] = useState<string | null>(null)

  function update(field: keyof typeof form, value: string) {
    setForm((current) => ({ ...current, [field]: value }))
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    try {
      await register({
        username: form.username.trim(),
        email: form.email.trim(),
        full_name: form.full_name.trim() || undefined,
        password: form.password,
      })
      await mergeGuestCart()
      navigate('/', { replace: true })
    } catch (caught) {
      setError(toApiError(caught).message)
    }
  }

  return (
    <div className="mx-auto max-w-md">
      <h1 className="font-display text-3xl text-ink-900">Create your account</h1>
      <p className="mt-1 text-sm text-ink-700">One account for your cart, orders and receipts.</p>

      <form onSubmit={handleSubmit} className="card mt-6 space-y-4 p-6">
        <ErrorBanner message={error} onDismiss={() => setError(null)} />

        <div>
          <label className="label" htmlFor="reg-username">
            Username
          </label>
          <input
            id="reg-username"
            className="input"
            required
            minLength={3}
            pattern="[A-Za-z0-9_.\-]+"
            title="Letters, numbers, dots, dashes and underscores"
            value={form.username}
            onChange={(event) => update('username', event.target.value)}
          />
        </div>

        <div>
          <label className="label" htmlFor="reg-email">
            Email
          </label>
          <input
            id="reg-email"
            type="email"
            className="input"
            required
            value={form.email}
            onChange={(event) => update('email', event.target.value)}
          />
        </div>

        <div>
          <label className="label" htmlFor="reg-name">
            Full name <span className="text-ink-700/60">(optional)</span>
          </label>
          <input
            id="reg-name"
            className="input"
            value={form.full_name}
            onChange={(event) => update('full_name', event.target.value)}
          />
        </div>

        <div>
          <label className="label" htmlFor="reg-password">
            Password
          </label>
          <input
            id="reg-password"
            type="password"
            className="input"
            required
            minLength={8}
            autoComplete="new-password"
            value={form.password}
            onChange={(event) => update('password', event.target.value)}
          />
          <p className="mt-1 text-xs text-ink-700">
            At least 8 characters, including one letter and one digit.
          </p>
        </div>

        <button type="submit" className="btn-primary w-full" disabled={loading}>
          {loading ? 'Creating account…' : 'Create account'}
        </button>

        <p className="text-center text-sm text-ink-700">
          Already registered?{' '}
          <Link to="/login" className="font-semibold text-brand-700 hover:underline">
            Sign in
          </Link>
        </p>
      </form>
    </div>
  )
}
