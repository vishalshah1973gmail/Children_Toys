import { type FormEvent, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { assetUrl, toApiError } from '../api/client'
import { ordersApi } from '../api/orders'
import ErrorBanner from '../components/ErrorBanner'
import { formatMoney } from '../lib/format'
import { useAuthStore } from '../store/authStore'
import { useCartStore } from '../store/cartStore'

type Step = 'contact' | 'shipping' | 'review'

const STEPS: { key: Step; label: string }[] = [
  { key: 'contact', label: 'Contact' },
  { key: 'shipping', label: 'Shipping' },
  { key: 'review', label: 'Review & pay' },
]

/** Three-step checkout that hands off to Stripe Checkout at the end. */
export default function CheckoutPage() {
  const user = useAuthStore((state) => state.user)
  const cart = useCartStore((state) => state.cart)
  const refresh = useCartStore((state) => state.refresh)
  const navigate = useNavigate()

  const [step, setStep] = useState<Step>('contact')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [email, setEmail] = useState(user?.email ?? '')
  const [address, setAddress] = useState({
    full_name: user?.full_name ?? '',
    line1: '',
    line2: '',
    city: '',
    state: '',
    postal_code: '',
    country: 'US',
  })

  useEffect(() => {
    void refresh()
  }, [refresh])

  const blocked = cart.items.some((line) => !line.in_stock)

  function update(field: keyof typeof address, value: string) {
    setAddress((current) => ({ ...current, [field]: value }))
  }

  async function placeOrder(event: FormEvent) {
    event.preventDefault()
    setSubmitting(true)
    setError(null)
    try {
      const session = await ordersApi.createCheckoutSession(email, {
        ...address,
        line2: address.line2 || null,
      })
      if (session.dev_mode) {
        // Stripe keys are absent: confirm locally so the flow still completes.
        await ordersApi.devConfirm(session.order_number)
        await refresh()
        navigate(`/checkout/success?order_number=${session.order_number}`, { replace: true })
        return
      }
      window.location.href = session.checkout_url
    } catch (caught) {
      setError(toApiError(caught).message)
      setSubmitting(false)
    }
  }

  if (cart.items.length === 0) {
    return (
      <div className="py-16 text-center">
        <h1 className="font-display text-2xl text-ink-900">Nothing to check out</h1>
        <Link to="/catalog" className="btn-primary mt-4">
          Browse toys
        </Link>
      </div>
    )
  }

  return (
    <div className="grid gap-8 lg:grid-cols-[1fr_340px]">
      <section>
        <h1 className="font-display text-2xl text-ink-900">Checkout</h1>

        <ol className="mt-4 flex items-center gap-2 text-sm">
          {STEPS.map((entry, index) => {
            const active = entry.key === step
            const complete = STEPS.findIndex((item) => item.key === step) > index
            return (
              <li key={entry.key} className="flex items-center gap-2">
                <span
                  className={`grid h-7 w-7 place-items-center rounded-full text-xs font-bold ${
                    active
                      ? 'bg-brand-600 text-white'
                      : complete
                        ? 'bg-emerald-600 text-white'
                        : 'bg-ink-800/10 text-ink-700'
                  }`}
                >
                  {index + 1}
                </span>
                <span className={active ? 'font-semibold text-ink-900' : 'text-ink-700'}>
                  {entry.label}
                </span>
                {index < STEPS.length - 1 && <span className="px-1 text-ink-700">—</span>}
              </li>
            )
          })}
        </ol>

        <ErrorBanner message={error} onDismiss={() => setError(null)} />

        {blocked && (
          <div className="mt-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800">
            One or more items exceed available stock. Adjust the quantities in your{' '}
            <Link to="/cart" className="font-semibold underline">
              cart
            </Link>{' '}
            before paying.
          </div>
        )}

        <form onSubmit={placeOrder} className="card mt-5 space-y-4 p-6">
          {step === 'contact' && (
            <>
              <div>
                <label className="label" htmlFor="checkout-email">
                  Email for the receipt
                </label>
                <input
                  id="checkout-email"
                  type="email"
                  className="input"
                  required
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                />
              </div>
              <button
                type="button"
                className="btn-primary"
                disabled={!email}
                onClick={() => setStep('shipping')}
              >
                Continue to shipping
              </button>
            </>
          )}

          {step === 'shipping' && (
            <>
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="sm:col-span-2">
                  <label className="label" htmlFor="ship-name">
                    Full name
                  </label>
                  <input
                    id="ship-name"
                    className="input"
                    required
                    value={address.full_name}
                    onChange={(event) => update('full_name', event.target.value)}
                  />
                </div>
                <div className="sm:col-span-2">
                  <label className="label" htmlFor="ship-line1">
                    Address
                  </label>
                  <input
                    id="ship-line1"
                    className="input"
                    required
                    value={address.line1}
                    onChange={(event) => update('line1', event.target.value)}
                  />
                </div>
                <div className="sm:col-span-2">
                  <label className="label" htmlFor="ship-line2">
                    Apartment, suite <span className="text-ink-700/60">(optional)</span>
                  </label>
                  <input
                    id="ship-line2"
                    className="input"
                    value={address.line2}
                    onChange={(event) => update('line2', event.target.value)}
                  />
                </div>
                <div>
                  <label className="label" htmlFor="ship-city">
                    City
                  </label>
                  <input
                    id="ship-city"
                    className="input"
                    required
                    value={address.city}
                    onChange={(event) => update('city', event.target.value)}
                  />
                </div>
                <div>
                  <label className="label" htmlFor="ship-state">
                    State
                  </label>
                  <input
                    id="ship-state"
                    className="input"
                    required
                    value={address.state}
                    onChange={(event) => update('state', event.target.value)}
                  />
                </div>
                <div>
                  <label className="label" htmlFor="ship-zip">
                    ZIP / postal code
                  </label>
                  <input
                    id="ship-zip"
                    className="input"
                    required
                    value={address.postal_code}
                    onChange={(event) => update('postal_code', event.target.value)}
                  />
                </div>
                <div>
                  <label className="label" htmlFor="ship-country">
                    Country
                  </label>
                  <input
                    id="ship-country"
                    className="input uppercase"
                    maxLength={2}
                    required
                    value={address.country}
                    onChange={(event) => update('country', event.target.value.toUpperCase())}
                  />
                </div>
              </div>

              <div className="flex gap-3">
                <button type="button" className="btn-secondary" onClick={() => setStep('contact')}>
                  Back
                </button>
                <button
                  type="button"
                  className="btn-primary"
                  disabled={
                    !address.full_name ||
                    !address.line1 ||
                    !address.city ||
                    !address.state ||
                    !address.postal_code
                  }
                  onClick={() => setStep('review')}
                >
                  Review order
                </button>
              </div>
            </>
          )}

          {step === 'review' && (
            <>
              <div className="rounded-lg bg-orange-50 p-4 text-sm">
                <p className="font-semibold text-ink-900">Shipping to</p>
                <p className="mt-1 text-ink-700">
                  {address.full_name}
                  <br />
                  {address.line1}
                  {address.line2 ? `, ${address.line2}` : ''}
                  <br />
                  {address.city}, {address.state} {address.postal_code}, {address.country}
                </p>
                <p className="mt-2 text-ink-700">Receipt to {email}</p>
              </div>

              <ul className="divide-y divide-ink-800/10">
                {cart.items.map((line) => (
                  <li key={line.id} className="flex items-center gap-3 py-3">
                    <img
                      src={assetUrl(line.image_url)}
                      alt={line.name}
                      className="h-12 w-12 rounded object-cover"
                    />
                    <span className="flex-1 text-sm">
                      {line.name} × {line.quantity}
                    </span>
                    <span className="text-sm font-medium">
                      {formatMoney(line.line_total_cents)}
                    </span>
                  </li>
                ))}
              </ul>

              <div className="flex gap-3">
                <button type="button" className="btn-secondary" onClick={() => setStep('shipping')}>
                  Back
                </button>
                <button type="submit" className="btn-primary flex-1" disabled={submitting || blocked}>
                  {submitting ? 'Redirecting to payment…' : `Pay ${formatMoney(cart.total_cents)}`}
                </button>
              </div>

              <p className="text-xs text-ink-700">
                Payment is taken by Stripe in test mode. Card 4242 4242 4242 4242, any future expiry
                and any CVC.
              </p>
            </>
          )}
        </form>
      </section>

      <aside className="card h-fit p-6">
        <h2 className="font-display text-xl text-ink-900">Summary</h2>
        <dl className="mt-4 space-y-2 text-sm">
          <div className="flex justify-between">
            <dt className="text-ink-700">Subtotal</dt>
            <dd>{formatMoney(cart.subtotal_cents)}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-ink-700">Shipping</dt>
            <dd>{cart.shipping_cents === 0 ? 'Free' : formatMoney(cart.shipping_cents)}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-ink-700">Tax</dt>
            <dd>{formatMoney(cart.tax_cents)}</dd>
          </div>
          <div className="flex justify-between border-t border-ink-800/10 pt-3 text-base font-bold">
            <dt>Total</dt>
            <dd>{formatMoney(cart.total_cents)}</dd>
          </div>
        </dl>
      </aside>
    </div>
  )
}
