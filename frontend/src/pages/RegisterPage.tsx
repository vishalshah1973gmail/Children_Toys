import { type FormEvent, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { toApiError } from '../api/client'
import Dialog from '../components/Dialog'
import ErrorBanner from '../components/ErrorBanner'
import SplitPage from '../components/SplitPage'
import { useAuthStore } from '../store/authStore'

/** Create a customer account. */
export default function RegisterPage() {
  const register = useAuthStore((state) => state.register)
  const loading = useAuthStore((state) => state.loading)
  const navigate = useNavigate()
  const [submitted, setSubmitted] = useState(false)

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
      setSubmitted(true)
    } catch (caught) {
      setError(toApiError(caught).message)
    }
  }

  return (
    <SplitPage
      eyebrow="Join ToyBox"
      title="Create your account"
      subtitle="One account for your cart and your orders."
    >
      <form onSubmit={handleSubmit} className="space-y-5">
        <ErrorBanner message={error} onDismiss={() => setError(null)} />

        <div>
          <label className="label text-base" htmlFor="reg-username">
            Username
          </label>
          <input
            id="reg-username"
            className="input py-3 text-base"
            required
            minLength={3}
            pattern="[A-Za-z0-9_.\-]+"
            title="Letters, numbers, dots, dashes and underscores"
            value={form.username}
            onChange={(event) => update('username', event.target.value)}
          />
        </div>

        <div>
          <label className="label text-base" htmlFor="reg-email">
            Email
          </label>
          <input
            id="reg-email"
            type="email"
            className="input py-3 text-base"
            required
            value={form.email}
            onChange={(event) => update('email', event.target.value)}
          />
        </div>

        <div>
          <label className="label text-base" htmlFor="reg-name">
            Full name <span className="text-ink-700/60">(optional)</span>
          </label>
          <input
            id="reg-name"
            className="input py-3 text-base"
            value={form.full_name}
            onChange={(event) => update('full_name', event.target.value)}
          />
        </div>

        <div>
          <label className="label text-base" htmlFor="reg-password">
            Password
          </label>
          <input
            id="reg-password"
            type="password"
            className="input py-3 text-base"
            required
            minLength={8}
            autoComplete="new-password"
            value={form.password}
            onChange={(event) => update('password', event.target.value)}
          />
          <p className="mt-1 text-sm text-ink-700">
            At least 8 characters, including one letter and one digit.
          </p>
        </div>

        <button type="submit" className="btn-primary w-full py-3 text-lg" disabled={loading}>
          {loading ? 'Creating account…' : 'Create account'}
        </button>

        <p className="text-center text-base text-ink-700">
          Already registered?{' '}
          <Link to="/login" className="font-semibold text-brand-700 hover:underline">
            Sign in
          </Link>
        </p>
      </form>

      {submitted && (
        <Dialog
          title="Registration submitted"
          onClose={() => navigate('/login', { replace: true })}
          actions={
            <button type="button" className="btn-primary px-5 py-2" onClick={() => navigate('/login', { replace: true })}>
              OK
            </button>
          }
        >
          Your registration approval is in progress. We have asked the site admin to review it,
          and you will get an email as soon as a decision is made. You can sign in once it is approved.
        </Dialog>
      )}
    </SplitPage>
  )
}
