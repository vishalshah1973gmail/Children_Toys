import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { assetUrl, toApiError } from '../api/client'
import { ordersApi } from '../api/orders'
import ErrorBanner from '../components/ErrorBanner'
import Spinner from '../components/Spinner'
import { STATUS_STYLES, formatDateTime, formatMoney } from '../lib/format'
import type { Order } from '../types'

const TIMELINE: { key: keyof Order; label: string }[] = [
  { key: 'placed_at', label: 'Placed' },
  { key: 'paid_at', label: 'Paid' },
  { key: 'shipped_at', label: 'Shipped' },
  { key: 'delivered_at', label: 'Delivered' },
]

/** One order with its lines, totals, address and payment trail. */
export default function OrderDetailPage() {
  const { orderNumber = '' } = useParams()
  const [order, setOrder] = useState<Order | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    ordersApi
      .get(orderNumber)
      .then((data) => {
        if (!cancelled) setOrder(data)
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
  }, [orderNumber])

  if (loading) return <Spinner />
  if (error || !order) {
    return (
      <div className="py-16 text-center">
        <ErrorBanner message={error ?? 'Order not found'} />
        <Link to="/orders" className="btn-primary mt-4">
          Back to orders
        </Link>
      </div>
    )
  }

  return (
    <div>
      <Link to="/orders" className="text-sm text-brand-700 hover:underline">
        ← All orders
      </Link>

      <div className="mt-3 flex flex-wrap items-center gap-3">
        <h1 className="font-display text-2xl text-ink-900">{order.order_number}</h1>
        <span className={`badge ${STATUS_STYLES[order.status]}`}>{order.status}</span>
      </div>

      <ol className="mt-5 grid gap-3 sm:grid-cols-4">
        {TIMELINE.map((entry) => {
          const value = order[entry.key] as string | null
          return (
            <li key={entry.label} className={`card p-4 ${value ? '' : 'opacity-50'}`}>
              <p className="text-xs uppercase tracking-wide text-ink-700">{entry.label}</p>
              <p className="mt-1 text-sm font-medium text-ink-900">{formatDateTime(value)}</p>
            </li>
          )
        })}
      </ol>

      <div className="mt-8 grid gap-6 lg:grid-cols-[1fr_320px]">
        <section className="card p-5">
          <h2 className="font-display text-lg text-ink-900">Items</h2>
          <ul className="mt-3 divide-y divide-ink-800/10">
            {order.items.map((item) => (
              <li key={item.id} className="flex items-center gap-4 py-3">
                <img
                  src={assetUrl(item.image_url)}
                  alt={item.product_name}
                  className="h-16 w-16 rounded-lg object-cover"
                />
                <div className="flex-1">
                  <Link
                    to={`/product/${item.product_slug}`}
                    className="font-medium text-ink-900 hover:text-brand-700"
                  >
                    {item.product_name}
                  </Link>
                  <p className="text-sm text-ink-700">
                    {formatMoney(item.unit_price_cents)} × {item.quantity}
                  </p>
                </div>
                <p className="font-semibold">{formatMoney(item.line_total_cents)}</p>
              </li>
            ))}
          </ul>
        </section>

        <aside className="space-y-4">
          <div className="card p-5">
            <h2 className="font-display text-lg text-ink-900">Totals</h2>
            <dl className="mt-3 space-y-2 text-sm">
              <div className="flex justify-between">
                <dt className="text-ink-700">Subtotal</dt>
                <dd>{formatMoney(order.subtotal_cents)}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-ink-700">Shipping</dt>
                <dd>
                  {order.shipping_cents === 0 ? 'Free' : formatMoney(order.shipping_cents)}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-ink-700">Tax</dt>
                <dd>{formatMoney(order.tax_cents)}</dd>
              </div>
              <div className="flex justify-between border-t border-ink-800/10 pt-2 font-bold">
                <dt>Total</dt>
                <dd>{formatMoney(order.total_cents)}</dd>
              </div>
            </dl>
          </div>

          <div className="card p-5 text-sm">
            <h2 className="font-display text-lg text-ink-900">Shipping to</h2>
            <p className="mt-2 text-ink-700">
              {order.shipping_name}
              <br />
              {order.shipping_line1}
              {order.shipping_line2 ? `, ${order.shipping_line2}` : ''}
              <br />
              {order.shipping_city}, {order.shipping_state} {order.shipping_postal_code}
              <br />
              {order.shipping_country}
            </p>
            <p className="mt-3 text-ink-700">Receipt: {order.contact_email}</p>
          </div>

          {order.payments.length > 0 && (
            <div className="card p-5 text-sm">
              <h2 className="font-display text-lg text-ink-900">Payments</h2>
              <ul className="mt-2 space-y-2">
                {order.payments.map((payment) => (
                  <li key={payment.id} className="flex justify-between">
                    <span className="text-ink-700">
                      {payment.provider} · {payment.status}
                    </span>
                    <span className="font-medium">{formatMoney(payment.amount_cents)}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </aside>
      </div>
    </div>
  )
}
