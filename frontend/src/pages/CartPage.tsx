import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { catalogApi } from '../api/catalog'
import { assetUrl } from '../api/client'
import ErrorBanner from '../components/ErrorBanner'
import { formatMoney } from '../lib/format'
import { useAuthStore } from '../store/authStore'
import { useCartStore } from '../store/cartStore'
import type { Product } from '../types'

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

  const [suggestions, setSuggestions] = useState<Product[]>([])
  const isEmpty = cart.items.length === 0

  useEffect(() => {
    void refresh()
  }, [refresh])

  useEffect(() => {
    if (!isEmpty) return
    let cancelled = false
    catalogApi
      .featured(6)
      .then((products) => {
        if (!cancelled) setSuggestions(products)
      })
      .catch(() => {
        // Suggestions are decoration; an empty cart still renders without them.
      })
    return () => {
      cancelled = true
    }
  }, [isEmpty])

  if (isEmpty) {
    return (
      <section className="card flex w-full flex-1 overflow-hidden bg-gradient-to-br from-orange-50 via-white to-orange-100">
        <div className="grid w-full gap-10 p-8 sm:p-12 xl:p-16 lg:grid-cols-[1fr_1.1fr] lg:items-center">
          <div>
            <p className="badge bg-orange-100 text-base text-brand-800">Your cart</p>
            <h1 className="mt-4 font-display text-5xl leading-tight text-ink-900 xl:text-7xl">
              Your cart is empty
            </h1>
            <p className="mt-5 max-w-xl text-xl leading-relaxed text-ink-700 xl:text-2xl">
              Pick something from the shelves and it will show up here. Every toy lists its real
              age range and safety notes.
            </p>
            <div className="mt-8 flex flex-wrap gap-4">
              <Link to="/catalog" className="btn-primary px-10 py-4 text-lg">
                Browse toys
              </Link>
              <Link to="/catalog?age_months=48" className="btn-secondary px-10 py-4 text-lg">
                Find by age
              </Link>
            </div>
          </div>
          {suggestions.length > 0 && (
            <div>
              <p className="mb-4 font-display text-2xl text-ink-900">Popular right now</p>
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 xl:gap-6">
                {suggestions.map((product) => (
                  <Link
                    key={product.id}
                    to={`/product/${product.slug}`}
                    className="group block overflow-hidden rounded-2xl bg-white shadow-sm ring-1 ring-ink-800/10 transition hover:-translate-y-0.5 hover:shadow-md"
                  >
                    <img
                      src={assetUrl(product.primary_image_url)}
                      alt={product.name}
                      className="aspect-square w-full object-cover"
                    />
                    <p className="line-clamp-2 p-3 font-display text-base text-ink-900 xl:text-lg">
                      {product.name}
                    </p>
                  </Link>
                ))}
              </div>
            </div>
          )}
        </div>
      </section>
    )
  }

  return (
    <div className="mx-auto grid w-full max-w-[1400px] gap-8 lg:grid-cols-[1fr_380px]">
      <section>
        <div className="mb-4 flex items-center justify-between">
          <h1 className="font-display text-3xl text-ink-900">Your cart</h1>
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
                  className="h-32 w-32 rounded-lg object-cover"
                />
              </Link>

              <div className="flex flex-1 flex-col">
                <Link
                  to={`/product/${line.slug}`}
                  className="font-display text-2xl text-ink-900 hover:text-brand-700"
                >
                  {line.name}
                </Link>
                <p className="text-base text-ink-700">{formatMoney(line.unit_price_cents)} each</p>
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

              <p className="self-center text-xl font-semibold text-ink-900">
                {formatMoney(line.line_total_cents)}
              </p>
            </li>
          ))}
        </ul>
      </section>

      <aside className="card h-fit p-6">
        <h2 className="font-display text-2xl text-ink-900">Order summary</h2>
        <dl className="mt-4 space-y-3 text-base">
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
          <div className="flex justify-between border-t border-ink-800/10 pt-3 text-xl">
            <dt className="font-semibold text-ink-900">Total</dt>
            <dd className="font-bold text-ink-900">{formatMoney(cart.total_cents)}</dd>
          </div>
        </dl>

        <div className="mt-5 space-y-2">
          <button
            type="button"
            className="btn-primary w-full py-3 text-lg"
            onClick={() => navigate(user ? '/checkout' : '/login', { state: { from: '/checkout' } })}
          >
            {user ? 'Proceed to checkout' : 'Sign in to check out'}
          </button>
          {!user && (
            <p className="text-center text-sm text-ink-700">
              Log in or register to check out.{' '}
              <Link to="/register" className="font-medium underline">
                Create an account
              </Link>
            </p>
          )}
        </div>

        <p className="mt-4 text-sm text-ink-700">
          Prices and stock are confirmed on the server before payment is taken.
        </p>
      </aside>
    </div>
  )
}
