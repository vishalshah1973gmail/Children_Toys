import { useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { assetUrl } from '../api/client'
import EmptyState from '../components/EmptyState'
import ErrorBanner from '../components/ErrorBanner'
import { formatMoney } from '../lib/format'
import { useAuthStore } from '../store/authStore'
import { useCartStore } from '../store/cartStore'

/** Cart page. Totals shown here are recomputed server-side at checkout. */
export default function CartPage() {
  const cart = useCartStore((state) => state.cart)
  const error = useCartStore((state) => state.error)
  const refresh = useCartStore((state) => state.refresh)
  const setQuantity = useCartStore((state) => state.setQuantity)
  const remove = useCartStore((state) => state.remove)
  const clear = useCartStore((state) => state.clear)
  const user = useAuthStore((state) => state.user)
  const navigate = useNavigate()

  useEffect(() => {
    void refresh()
  }, [refresh])

  if (cart.items.length === 0) {
    return (
      <EmptyState
        title="Your cart is empty"
        description="Pick something from the shelves and it will show up here."
        action={
          <Link to="/catalog" className="btn-primary">
            Browse toys
          </Link>
        }
      />
    )
  }

  return (
    <div className="grid gap-8 lg:grid-cols-[1fr_340px]">
      <section>
        <div className="mb-4 flex items-center justify-between">
          <h1 className="font-display text-2xl text-ink-900">Your cart</h1>
          <button type="button" className="btn-ghost text-sm" onClick={() => void clear()}>
            Empty cart
          </button>
        </div>

        <ErrorBanner message={error} />

        <ul className="space-y-3">
          {cart.items.map((line) => (
            <li key={line.id} className="card flex gap-4 p-4">
              <Link to={`/product/${line.slug}`} className="shrink-0">
                <img
                  src={assetUrl(line.image_url)}
                  alt={line.name}
                  className="h-24 w-24 rounded-lg object-cover"
                />
              </Link>

              <div className="flex flex-1 flex-col">
                <Link
                  to={`/product/${line.slug}`}
                  className="font-display text-lg text-ink-900 hover:text-brand-700"
                >
                  {line.name}
                </Link>
                <p className="text-sm text-ink-700">{formatMoney(line.unit_price_cents)} each</p>
                {!line.in_stock && (
                  <p className="mt-1 text-sm font-semibold text-red-600">
                    Only {line.stock_quantity} left — reduce the quantity to check out.
                  </p>
                )}

                <div className="mt-auto flex items-center gap-3 pt-3">
                  <input
                    type="number"
                    min={1}
                    max={line.stock_quantity}
                    value={line.quantity}
                    aria-label={`Quantity for ${line.name}`}
                    onChange={(event) => void setQuantity(line, Number(event.target.value))}
                    className="input w-20"
                  />
                  <button
                    type="button"
                    className="text-sm text-red-700 hover:underline"
                    onClick={() => void remove(line)}
                  >
                    Remove
                  </button>
                </div>
              </div>

              <p className="self-center font-semibold text-ink-900">
                {formatMoney(line.line_total_cents)}
              </p>
            </li>
          ))}
        </ul>
      </section>

      <aside className="card h-fit p-6">
        <h2 className="font-display text-xl text-ink-900">Order summary</h2>
        <dl className="mt-4 space-y-2 text-sm">
          <div className="flex justify-between">
            <dt className="text-ink-700">Subtotal</dt>
            <dd className="font-medium">{formatMoney(cart.subtotal_cents)}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-ink-700">Shipping</dt>
            <dd className="font-medium">
              {cart.shipping_cents === 0 ? 'Free' : formatMoney(cart.shipping_cents)}
            </dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-ink-700">Estimated tax</dt>
            <dd className="font-medium">{formatMoney(cart.tax_cents)}</dd>
          </div>
          <div className="flex justify-between border-t border-ink-800/10 pt-3 text-base">
            <dt className="font-semibold text-ink-900">Total</dt>
            <dd className="font-bold text-ink-900">{formatMoney(cart.total_cents)}</dd>
          </div>
        </dl>

        <div className="mt-5 space-y-2">
          <button
            type="button"
            className="btn-primary w-full"
            onClick={() => navigate(user ? '/checkout' : '/login', { state: { from: '/checkout' } })}
          >
            {user ? 'Proceed to checkout' : 'Sign in to check out'}
          </button>
          {!user && (
            <button
              type="button"
              className="btn-secondary w-full"
              onClick={() => navigate('/checkout/guest')}
            >
              Checkout as guest
            </button>
          )}
        </div>

        <p className="mt-3 text-xs text-ink-700">
          Prices and stock are confirmed on the server before payment is taken.
        </p>
      </aside>
    </div>
  )
}
