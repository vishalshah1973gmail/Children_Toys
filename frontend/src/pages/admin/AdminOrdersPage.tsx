import { Fragment, useCallback, useEffect, useState } from 'react'

import { adminApi } from '../../api/admin'
import { toApiError } from '../../api/client'
import ErrorBanner from '../../components/ErrorBanner'
import Pagination from '../../components/Pagination'
import Spinner from '../../components/Spinner'
import { STATUS_STYLES, formatDate, formatMoney } from '../../lib/format'
import type { Order, OrderStatus, Paged } from '../../types'

const FILTERS: { value: '' | OrderStatus; label: string }[] = [
  { value: '', label: 'All' },
  { value: 'pending', label: 'Pending' },
  { value: 'paid', label: 'Paid' },
  { value: 'shipped', label: 'Shipped' },
  { value: 'delivered', label: 'Delivered' },
  { value: 'cancelled', label: 'Cancelled' },
]

/** The next status an order can be advanced to from the dashboard. */
const NEXT_STATUS: Partial<Record<OrderStatus, OrderStatus>> = {
  pending: 'paid',
  paid: 'shipped',
  shipped: 'delivered',
}

/** All orders with one-click status advancement. */
export default function AdminOrdersPage() {
  const [result, setResult] = useState<Paged<Order> | null>(null)
  const [status, setStatus] = useState<'' | OrderStatus>('')
  const [page, setPage] = useState(1)
  const [expanded, setExpanded] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      setResult(await adminApi.orders(page, 20, status || undefined))
      setError(null)
    } catch (caught) {
      setError(toApiError(caught).message)
    } finally {
      setLoading(false)
    }
  }, [page, status])

  useEffect(() => {
    void load()
  }, [load])

  async function advance(order: Order) {
    const next = NEXT_STATUS[order.status]
    if (!next) return
    try {
      await adminApi.setOrderStatus(order.order_number, next)
      await load()
    } catch (caught) {
      setError(toApiError(caught).message)
    }
  }

  return (
    <div>
      <div className="mb-4 flex flex-wrap gap-2">
        {FILTERS.map((filter) => (
          <button
            key={filter.label}
            type="button"
            onClick={() => {
              setPage(1)
              setStatus(filter.value)
            }}
            className={
              status === filter.value
                ? 'btn bg-ink-900 text-white'
                : 'btn-secondary'
            }
          >
            {filter.label}
          </button>
        ))}
      </div>

      <ErrorBanner message={error} onDismiss={() => setError(null)} />

      {loading && !result ? (
        <Spinner />
      ) : (
        <div className="card overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-ink-800/10 text-xs uppercase tracking-wide text-ink-700">
              <tr>
                <th className="px-4 py-3">Order</th>
                <th className="px-4 py-3">Placed</th>
                <th className="px-4 py-3">Ship to</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3 text-right">Total</th>
                <th className="px-4 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-ink-800/5">
              {result?.items.map((order) => (
                <Fragment key={order.id}>
                  <tr>
                    <td className="px-4 py-3">
                      <button
                        type="button"
                        className="font-medium text-brand-700 hover:underline"
                        onClick={() =>
                          setExpanded(expanded === order.order_number ? null : order.order_number)
                        }
                      >
                        {order.order_number}
                      </button>
                    </td>
                    <td className="px-4 py-3 text-ink-700">{formatDate(order.placed_at)}</td>
                    <td className="px-4 py-3 text-ink-700">
                      {order.shipping_name} · {order.shipping_city}, {order.shipping_state}
                    </td>
                    <td className="px-4 py-3">
                      <span className={`badge ${STATUS_STYLES[order.status]}`}>{order.status}</span>
                    </td>
                    <td className="px-4 py-3 text-right font-semibold">
                      {formatMoney(order.total_cents)}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {NEXT_STATUS[order.status] ? (
                        <button
                          type="button"
                          className="btn-secondary"
                          onClick={() => void advance(order)}
                        >
                          Mark {NEXT_STATUS[order.status]}
                        </button>
                      ) : (
                        <span className="text-xs text-ink-700">—</span>
                      )}
                    </td>
                  </tr>
                  {expanded === order.order_number && (
                    <tr className="bg-orange-50/50">
                      <td colSpan={6} className="px-4 py-3">
                        <ul className="space-y-1 text-sm">
                          {order.items.map((item) => (
                            <li key={item.id} className="flex justify-between">
                              <span>
                                {item.product_name} × {item.quantity}
                              </span>
                              <span>{formatMoney(item.line_total_cents)}</span>
                            </li>
                          ))}
                        </ul>
                        <p className="mt-2 text-xs text-ink-700">
                          {order.shipping_line1}
                          {order.shipping_line2 ? `, ${order.shipping_line2}` : ''},{' '}
                          {order.shipping_city}, {order.shipping_state}{' '}
                          {order.shipping_postal_code} · {order.contact_email}
                        </p>
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Pagination page={result?.page ?? 1} pages={result?.pages ?? 1} onChange={setPage} />
    </div>
  )
}
