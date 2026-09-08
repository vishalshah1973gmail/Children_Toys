import { type FormEvent, useState } from 'react'

import { authApi } from '../api/auth'
import { toApiError } from '../api/client'
import ErrorBanner from '../components/ErrorBanner'
import { formatDate } from '../lib/format'
import { useAuthStore } from '../store/authStore'

/** Account details and password change. */
export default function AccountPage() {
  const user = useAuthStore((state) => state.user)
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setMessage(null)
    setSaving(true)
    try {
      await authApi.changePassword(currentPassword, newPassword)
      setMessage('Password updated.')
      setCurrentPassword('')
      setNewPassword('')
    } catch (caught) {
      setError(toApiError(caught).message)
    } finally {
      setSaving(false)
    }
  }

  if (!user) return null

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <h1 className="font-display text-2xl text-ink-900">Your account</h1>

      <dl className="card grid gap-3 p-6 text-sm sm:grid-cols-2">
        <div>
          <dt className="text-ink-700">Username</dt>
          <dd className="font-medium text-ink-900">{user.username}</dd>
        </div>
        <div>
          <dt className="text-ink-700">Email</dt>
          <dd className="font-medium text-ink-900">{user.email}</dd>
        </div>
        <div>
          <dt className="text-ink-700">Name</dt>
          <dd className="font-medium text-ink-900">{user.full_name ?? '—'}</dd>
        </div>
        <div>
          <dt className="text-ink-700">Role</dt>
          <dd className="font-medium text-ink-900">{user.role}</dd>
        </div>
        <div>
          <dt className="text-ink-700">Member since</dt>
          <dd className="font-medium text-ink-900">{formatDate(user.created_at)}</dd>
        </div>
      </dl>

      <form onSubmit={handleSubmit} className="card space-y-4 p-6">
        <h2 className="font-display text-lg text-ink-900">Change password</h2>
        <ErrorBanner message={error} onDismiss={() => setError(null)} />
        {message && (
          <p className="rounded-lg bg-emerald-50 px-4 py-2 text-sm text-emerald-800">{message}</p>
        )}

        <div>
          <label className="label" htmlFor="current-password">
            Current password
          </label>
          <input
            id="current-password"
            type="password"
            className="input"
            required
            autoComplete="current-password"
            value={currentPassword}
            onChange={(event) => setCurrentPassword(event.target.value)}
          />
        </div>

        <div>
          <label className="label" htmlFor="new-password">
            New password
          </label>
          <input
            id="new-password"
            type="password"
            className="input"
            required
            minLength={8}
            autoComplete="new-password"
            value={newPassword}
            onChange={(event) => setNewPassword(event.target.value)}
          />
        </div>

        <button type="submit" className="btn-primary" disabled={saving}>
          {saving ? 'Updating…' : 'Update password'}
        </button>
      </form>
    </div>
  )
}
