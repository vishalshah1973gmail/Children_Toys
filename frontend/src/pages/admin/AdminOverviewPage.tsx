import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { adminApi } from '../../api/admin'
import { toApiError } from '../../api/client'
import ErrorBanner from '../../components/ErrorBanner'
import Spinner from '../../components/Spinner'
import { STATUS_STYLES, formatDate, formatMoney } from '../../lib/format'
import type { AdminStats, Order } from '../../types'

/** Headline numbers plus the most recent orders. */
export default function AdminOverviewPage() {
  const [stats, setStats] = useState<AdminStats | null>(null)
  const [recent, setRecent] = useState<Order[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const [statsData, orders] = await Promise.all([
          adminApi.stats(),
          adminApi.orders(1, 8),
        ])
        if (cancelled) return
        setStats(statsData)
        setRecent(orders.items)
      } catch (caught) {
        if (!cancelled) setError(toApiError(caught).message)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [])

  if (loading) return <Spinner label="Loading dashboard…" />

  const tiles = stats
    ? [
        { label: 'Revenue (paid+)', value: formatMoney(stats.revenue_cents) },
        { label: 'Orders', value: String(stats.orders) },
        { label: 'Pending orders', value: String(stats.pending_orders) },
        { label: 'Customers', value: String(stats.customers) },
        { label: 'Active products', value: `${stats.active_products}/${stats.products}` },
        { label: 'Low stock (<5)', value: String(stats.low_stock) },
      ]
    : []

  return (
    <div className="space-y-8">
      <ErrorBanner message={error} />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {tiles.map((tile) => (
          <div key={tile.label} className="card p-5">
            <p className="text-sm text-ink-700">{tile.label}</p>
            <p className="mt-1 font-display text-2xl text-ink-900">{tile.value}</p>
          </div>
        ))}
      </div>

      <section>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="font-display text-xl text-ink-900">Recent orders</h2>
          <Link to="/admin/orders" className="text-sm font-semibold text-brand-700 hover:underline">
            All orders →
          </Link>
        </div>

        <div className="card overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-ink-800/10 text-xs uppercase tracking-wide text-ink-700">
              <tr>
                <th className="px-4 py-3">Order</th>
                <th className="px-4 py-3">Placed</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3 text-right">Total</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-ink-800/5">
              {recent.map((order) => (
                <tr key={order.id}>
                  <td className="px-4 py-3 font-medium">{order.order_number}</td>
                  <td className="px-4 py-3 text-ink-700">{formatDate(order.placed_at)}</td>
                  <td className="px-4 py-3">
                    <span className={`badge ${STATUS_STYLES[order.status]}`}>{order.status}</span>
                  </td>
                  <td className="px-4 py-3 text-right font-semibold">
                    {formatMoney(order.total_cents)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
