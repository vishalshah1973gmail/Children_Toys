import { useCallback, useEffect, useState } from 'react'

import { adminApi } from '../../api/admin'
import { toApiError } from '../../api/client'
import Dialog from '../../components/Dialog'
import ErrorBanner from '../../components/ErrorBanner'
import Spinner from '../../components/Spinner'
import { formatDate } from '../../lib/format'
import type { Registration } from '../../types'

/** Pending registrations with Approve / Reject (reason required). */
export default function AdminApprovalsPage() {
  const [items, setItems] = useState<Registration[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [busyId, setBusyId] = useState<number | null>(null)
  const [rejecting, setRejecting] = useState<Registration | null>(null)
  const [reason, setReason] = useState('')

  const load = useCallback(async () => {
    try {
      setItems((await adminApi.registrations(1, 100)).items)
    } catch (caught) {
      setError(toApiError(caught).message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  function report(name: string, verb: string, emailSent: boolean) {
    setNotice(
      emailSent
        ? `${name} ${verb}. The applicant was emailed.`
        : `${name} ${verb}, but the email could not be sent. Please contact them directly.`,
    )
  }

  async function approve(user: Registration) {
    setBusyId(user.id)
    setError(null)
    try {
      const result = await adminApi.approveRegistration(user.id)
      report(user.username, 'approved', result.email_sent)
    } catch (caught) {
      setError(toApiError(caught).message)
    } finally {
      setBusyId(null)
      await load()
    }
  }

  async function confirmReject() {
    if (!rejecting) return
    const target = rejecting
    setBusyId(target.id)
    setError(null)
    try {
      const result = await adminApi.rejectRegistration(target.id, reason.trim())
      report(target.username, 'rejected', result.email_sent)
      setRejecting(null)
      setReason('')
    } catch (caught) {
      setError(toApiError(caught).message)
    } finally {
      setBusyId(null)
      await load()
    }
  }

  if (loading) return <Spinner label="Loading registrations…" />

  const reasonTooShort = reason.trim().length < 5

  return (
    <div className="space-y-4">
      <ErrorBanner message={error} onDismiss={() => setError(null)} />
      {notice && (
        <p role="status" className="rounded-lg bg-green-50 px-4 py-3 text-sm text-green-800">
          {notice}
        </p>
      )}

      {items.length === 0 ? (
        <p className="card p-6 text-ink-700">No registrations are waiting for approval.</p>
      ) : (
        <div className="card overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-ink-800/10 text-xs uppercase tracking-wide text-ink-700">
              <tr>
                <th className="px-4 py-3">Name</th>
                <th className="px-4 py-3">Username</th>
                <th className="px-4 py-3">Email</th>
                <th className="px-4 py-3">Requested</th>
                <th className="px-4 py-3 text-right">Decision</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-ink-800/5">
              {items.map((user) => (
                <tr key={user.id}>
                  <td className="px-4 py-3 font-medium">{user.full_name ?? '—'}</td>
                  <td className="px-4 py-3">{user.username}</td>
                  <td className="px-4 py-3">{user.email}</td>
                  <td className="px-4 py-3 text-ink-700">{formatDate(user.created_at)}</td>
                  <td className="px-4 py-3">
                    <div className="flex justify-end gap-2">
                      <button
                        type="button"
                        className="btn-primary px-3 py-1.5 text-sm"
                        disabled={busyId === user.id}
                        onClick={() => void approve(user)}
                      >
                        Approve
                      </button>
                      <button
                        type="button"
                        className="rounded-lg px-3 py-1.5 text-sm font-semibold text-red-700 ring-1 ring-red-300 hover:bg-red-50 disabled:opacity-50"
                        disabled={busyId === user.id}
                        onClick={() => {
                          setReason('')
                          setRejecting(user)
                        }}
                      >
                        Reject
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {rejecting && (
        <Dialog
          title={`Reject ${rejecting.username}?`}
          onClose={() => setRejecting(null)}
          actions={
            <>
              <button
                type="button"
                className="rounded-lg px-3 py-2 text-sm font-medium text-ink-700 hover:bg-orange-100"
                onClick={() => setRejecting(null)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="rounded-lg bg-red-600 px-3 py-2 text-sm font-semibold text-white hover:bg-red-700 disabled:opacity-50"
                disabled={reasonTooShort || busyId === rejecting.id}
                onClick={() => void confirmReject()}
              >
                Reject and email
              </button>
            </>
          }
        >
          <label className="label" htmlFor="reject-reason">
            Reason (emailed to the applicant, 5–500 characters)
          </label>
          <textarea
            id="reject-reason"
            className="input mt-1 h-28 w-full"
            maxLength={500}
            autoFocus
            value={reason}
            onChange={(event) => setReason(event.target.value)}
          />
        </Dialog>
      )}
    </div>
  )
}
