import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'

import { toApiError } from '../api/client'
import { ordersApi } from '../api/orders'
import ErrorBanner from '../components/ErrorBanner'
import Spinner from '../components/Spinner'
import { formatMoney } from '../lib/format'
import { useCartStore } from '../store/cartStore'
import type { Order } from '../types'

/**
 * Landing page after Stripe redirects back. The order is confirmed by the
 * webhook, not by this page, so it polls briefly for the status to flip.
 */
export default function CheckoutSuccessPage() {
  const [searchParams] = useSearchParams()
  const orderNumber = searchParams.get('order_number') ?? ''
  const [order, setOrder] = useState<Order | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [waiting, setWaiting] = useState(true)
  const refreshCart = useCartStore((state) => state.refresh)

  useEffect(() => {
    if (!orderNumber) {
      setWaiting(false)
      setError('No order number was supplied.')
      return
    }

    let cancelled = false
    let attempts = 0

    async function poll() {
      try {
        const data = await ordersApi.get(orderNumber)
        if (cancelled) return
        setOrder(data)
        if (data.status === 'pending' && attempts < 6) {
          attempts += 1
          window.setTimeout(poll, 1500)
          return
        }
        setWaiting(false)
        void refreshCart()
      } catch (caught) {
        if (cancelled) return
        setError(toApiError(caught).message)
        setWaiting(false)
      }
    }

    void poll()
    return () => {
      cancelled = true
    }
  }, [orderNumber, refreshCart])

  if (waiting) return <Spinner label="Confirming your payment…" />

  return (
    <div className="mx-auto max-w-2xl py-8 text-center">
      <ErrorBanner message={error} />

      {order && (
        <>
          <div className="mx-auto grid h-16 w-16 place-items-center rounded-full bg-emerald-100 text-3xl">
            🎉
          </div>
          <h1 className="mt-4 font-display text-3xl text-ink-900">
            {order.status === 'pending' ? 'Order placed' : 'Payment confirmed'}
          </h1>
          <p className="mt-2 text-ink-700">
            Order <span className="font-semibold">{order.order_number}</span> for{' '}
            {formatMoney(order.total_cents)}.
          </p>
          {order.status === 'pending' && (
            <p className="mt-2 text-sm text-amber-700">
              Stripe has not confirmed the payment yet. This page updates once the webhook lands —
              your order history will show it as paid.
            </p>
          )}

          <ul className="card mt-6 divide-y divide-ink-800/10 p-4 text-left">
            {order.items.map((item) => (
              <li key={item.id} className="flex justify-between py-2 text-sm">
                <span>
                  {item.product_name} × {item.quantity}
                </span>
                <span className="font-medium">{formatMoney(item.line_total_cents)}</span>
              </li>
            ))}
          </ul>

          <div className="mt-6 flex justify-center gap-3">
            <Link to={`/orders/${order.order_number}`} className="btn-secondary">
              View order
            </Link>
            <Link to="/catalog" className="btn-primary">
              Keep shopping
            </Link>
          </div>
        </>
      )}
    </div>
  )
}
