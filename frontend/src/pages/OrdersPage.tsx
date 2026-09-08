import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { toApiError } from '../api/client'
import { ordersApi } from '../api/orders'
import EmptyState from '../components/EmptyState'
import ErrorBanner from '../components/ErrorBanner'
import Pagination from '../components/Pagination'
import Spinner from '../components/Spinner'
import { STATUS_STYLES, formatDate, formatMoney } from '../lib/format'
import type { Order, Paged } from '../types'

/** Order history for the signed-in shopper. */
export default function OrdersPage() {
  const [page, setPage] = useState(1)
  const [result, setResult] = useState<Paged<Order> | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    ordersApi
      .list(page, 10)
      .then((data) => {
        if (!cancelled) setResult(data)
      })
      .catch((caught) => {
        if (!cancelled) setError(toApiError(caught).message)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [page])

  if (loading && !result) return <Spinner label="Loading your orders…" />

  return (
    <div>
      <h1 className="font-display text-2xl text-ink-900">Your orders</h1>
      <ErrorBanner message={error} />

      {result && result.items.length === 0 ? (
        <EmptyState
          title="No orders yet"
          description="When you buy something it will appear here with its status and receipt."
          action={
            <Link to="/catalog" className="btn-primary">
              Start shopping
            </Link>
          }
        />
      ) : (
        <>
          <ul className="mt-4 space-y-3">
            {result?.items.map((order) => (
              <li key={order.id} className="card flex flex-wrap items-center gap-4 p-4">
                <div className="min-w-40">
                  <Link
                    to={`/orders/${order.order_number}`}
                    className="font-semibold text-ink-900 hover:text-brand-700"
                  >
                    {order.order_number}
                  </Link>
                  <p className="text-sm text-ink-700">{formatDate(order.placed_at)}</p>
                </div>

                <span className={`badge ${STATUS_STYLES[order.status]}`}>{order.status}</span>

                <p className="text-sm text-ink-700">
                  {order.items.reduce((sum, item) => sum + item.quantity, 0)} item(s)
                </p>

                <p className="ml-auto font-semibold text-ink-900">
                  {formatMoney(order.total_cents)}
                </p>

                <Link to={`/orders/${order.order_number}`} className="btn-secondary">
                  Details
                </Link>
              </li>
            ))}
          </ul>

          <Pagination page={result?.page ?? 1} pages={result?.pages ?? 1} onChange={setPage} />
        </>
      )}
    </div>
  )
}
