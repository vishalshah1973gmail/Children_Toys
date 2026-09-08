import { type FormEvent, useState } from 'react'
import { Link } from 'react-router-dom'

import { assetUrl, toApiError } from '../api/client'
import { ordersApi } from '../api/orders'
import ErrorBanner from '../components/ErrorBanner'
import { validateCard } from '../lib/cardValidation'
import { formatMoney } from '../lib/format'
import { useCartStore } from '../store/cartStore'
import type { CardBrand, GuestAddressInput, GuestCheckoutResponseBody } from '../types'

type Step = 'billing' | 'payment' | 'shipping' | 'review'

const STEPS: { key: Step; label: string }[] = [
  { key: 'billing', label: 'Contact & billing' },
  { key: 'payment', label: 'Payment' },
  { key: 'shipping', label: 'Shipping' },
  { key: 'review', label: 'Review' },
]

const EMPTY_ADDRESS: GuestAddressInput = {
  name: '', line1: '', line2: '', city: '', state: '', postal_code: '', country: 'US',
}

/** Guest checkout: no account, one request, order created already paid (simulated). */
export default function GuestCheckoutPage() {
  const cart = useCartStore((state) => state.cart)
  const clearCart = useCartStore((state) => state.clear)

  const [step, setStep] = useState<Step>('billing')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [receipt, setReceipt] = useState<GuestCheckoutResponseBody | null>(null)

  const [email, setEmail] = useState('')
  const [billing, setBilling] = useState<GuestAddressInput>(EMPTY_ADDRESS)
  const [sameAsBilling, setSameAsBilling] = useState(true)
  const [shipping, setShipping] = useState<GuestAddressInput>(EMPTY_ADDRESS)

  const [brand, setBrand] = useState<CardBrand>('visa')
  const [number, setNumber] = useState('')
  const [nameOnCard, setNameOnCard] = useState('')
  const [expMonth, setExpMonth] = useState(1)
  const [expYear, setExpYear] = useState(new Date().getFullYear())
  const [cvv, setCvv] = useState('')
  const [cardZip, setCardZip] = useState('')

  function updateBilling(field: keyof GuestAddressInput, value: string) {
    setBilling((current) => ({ ...current, [field]: value }))
  }
  function updateShipping(field: keyof GuestAddressInput, value: string) {
    setShipping((current) => ({ ...current, [field]: value }))
  }

  function validatePaymentStep(): boolean {
    const errors = validateCard({
      brand, number, expMonth, expYear, cvv, postalCode: cardZip,
    })
    setFieldErrors(errors)
    return Object.keys(errors).length === 0
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    setSubmitting(true)
    setError(null)
    try {
      const response = await ordersApi.guestCheckout({
        contact_email: email,
        billing_address: billing,
        card: {
          brand, number, name_on_card: nameOnCard, exp_month: expMonth,
          exp_year: expYear, cvv, postal_code: cardZip,
        },
        same_as_billing: sameAsBilling,
        shipping_address: sameAsBilling ? null : shipping,
        items: cart.items.map((line) => ({ product_id: line.product_id, quantity: line.quantity })),
      })
      setReceipt(response)
      await clearCart()
    } catch (caught) {
      setError(toApiError(caught).message)
    } finally {
      setSubmitting(false)
    }
  }

  if (receipt) {
    const { order, email_sent } = receipt
    return (
      <div className="mx-auto max-w-2xl py-8 text-center">
        <h1 className="font-display text-3xl text-ink-900">Order placed</h1>
        <p className="mt-2 text-ink-700">
          Order <span className="font-semibold">{order.order_number}</span> for{' '}
          {formatMoney(order.total_cents)}.
        </p>
        <p className="mt-2 text-sm text-ink-700">
          {email_sent
            ? `A receipt was emailed to ${order.contact_email}.`
            : "We couldn't email your receipt, but your order is confirmed below."}
        </p>
        <ul className="card mt-6 divide-y divide-ink-800/10 p-4 text-left">
          {order.items.map((item) => (
            <li key={item.id} className="flex items-center gap-3 py-3">
              <img src={assetUrl(item.image_url)} alt={item.product_name} className="h-12 w-12 rounded object-cover" />
              <span className="flex-1 text-sm">{item.product_name} × {item.quantity}</span>
              <span className="text-sm font-medium">{formatMoney(item.line_total_cents)}</span>
            </li>
          ))}
        </ul>
        <div className="card mt-4 p-4 text-left text-sm">
          <p className="font-semibold text-ink-900">Shipping to</p>
          <p className="mt-1 text-ink-700">
            {order.shipping_name}<br />
            {order.shipping_line1}{order.shipping_line2 ? `, ${order.shipping_line2}` : ''}<br />
            {order.shipping_city}, {order.shipping_state} {order.shipping_postal_code}
          </p>
        </div>
        <Link to="/catalog" className="btn-primary mt-6 inline-block">Keep shopping</Link>
      </div>
    )
  }

  if (cart.items.length === 0) {
    return (
      <div className="py-16 text-center">
        <h1 className="font-display text-2xl text-ink-900">Nothing to check out</h1>
        <Link to="/catalog" className="btn-primary mt-4">Browse toys</Link>
      </div>
    )
  }

  return (
    <div className="grid gap-8 lg:grid-cols-[1fr_340px]">
      <section>
        <h1 className="font-display text-2xl text-ink-900">Checkout as guest</h1>
        <ol className="mt-4 flex flex-wrap items-center gap-2 text-sm">
          {STEPS.map((entry) => (
            <li key={entry.key} className={entry.key === step ? 'font-semibold text-ink-900' : 'text-ink-700'}>
              {entry.label}
            </li>
          ))}
        </ol>

        <ErrorBanner message={error} onDismiss={() => setError(null)} />

        <form onSubmit={submit} className="card mt-5 space-y-4 p-6">
          {step === 'billing' && (
            <>
              <div>
                <label className="label" htmlFor="guest-email">Email for the receipt</label>
                <input id="guest-email" type="email" className="input" required
                  value={email} onChange={(event) => setEmail(event.target.value)} />
              </div>
              <div>
                <label className="label" htmlFor="billing-name">Full name</label>
                <input id="billing-name" className="input" required
                  value={billing.name} onChange={(event) => updateBilling('name', event.target.value)} />
              </div>
              <div>
                <label className="label" htmlFor="billing-line1">Street line 1</label>
                <input id="billing-line1" className="input" required
                  value={billing.line1} onChange={(event) => updateBilling('line1', event.target.value)} />
              </div>
              <div>
                <label className="label" htmlFor="billing-line2">Street line 2 (optional)</label>
                <input id="billing-line2" className="input"
                  value={billing.line2 ?? ''} onChange={(event) => updateBilling('line2', event.target.value)} />
              </div>
              <div className="grid gap-4 sm:grid-cols-3">
                <input className="input" placeholder="City" required
                  value={billing.city} onChange={(event) => updateBilling('city', event.target.value)} />
                <input className="input" placeholder="State" required
                  value={billing.state} onChange={(event) => updateBilling('state', event.target.value)} />
                <input className="input" placeholder="Zip" required
                  value={billing.postal_code} onChange={(event) => updateBilling('postal_code', event.target.value)} />
              </div>
              <button type="button" className="btn-primary"
                disabled={!email || !billing.name || !billing.line1 || !billing.city || !billing.state || !billing.postal_code}
                onClick={() => setStep('payment')}>
                Continue to payment
              </button>
            </>
          )}

          {step === 'payment' && (
            <>
              <div>
                <label className="label" htmlFor="card-brand">Card type</label>
                <select id="card-brand" className="input" value={brand}
                  onChange={(event) => setBrand(event.target.value as CardBrand)}>
                  <option value="visa">Visa</option>
                  <option value="mastercard">Mastercard</option>
                  <option value="discover">Discover</option>
                  <option value="amex">American Express</option>
                </select>
              </div>
              <div>
                <label className="label" htmlFor="card-number">Card number</label>
                <input id="card-number" className="input" required value={number}
                  onChange={(event) => setNumber(event.target.value)} />
                {fieldErrors.number && <p className="mt-1 text-sm text-red-600">{fieldErrors.number}</p>}
              </div>
              <div>
                <label className="label" htmlFor="card-name">Name on card</label>
                <input id="card-name" className="input" required value={nameOnCard}
                  onChange={(event) => setNameOnCard(event.target.value)} />
              </div>
              <div className="grid gap-4 sm:grid-cols-4">
                <input className="input" type="number" placeholder="MM" min={1} max={12} required
                  value={expMonth} onChange={(event) => setExpMonth(Number(event.target.value))} />
                <input className="input" type="number" placeholder="YYYY" min={2026} max={2100} required
                  value={expYear} onChange={(event) => setExpYear(Number(event.target.value))} />
                <input className="input" placeholder="CVV" required value={cvv}
                  onChange={(event) => setCvv(event.target.value)} />
                <input className="input" placeholder="Zip" required value={cardZip}
                  onChange={(event) => setCardZip(event.target.value)} />
              </div>
              {(fieldErrors.exp_month || fieldErrors.exp_year || fieldErrors.cvv || fieldErrors.postal_code) && (
                <p className="text-sm text-red-600">
                  {fieldErrors.exp_month || fieldErrors.exp_year || fieldErrors.cvv || fieldErrors.postal_code}
                </p>
              )}
              <div className="flex gap-3">
                <button type="button" className="btn-secondary" onClick={() => setStep('billing')}>Back</button>
                <button type="button" className="btn-primary" onClick={() => validatePaymentStep() && setStep('shipping')}>
                  Continue to shipping
                </button>
              </div>
            </>
          )}

          {step === 'shipping' && (
            <>
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={sameAsBilling}
                  onChange={(event) => setSameAsBilling(event.target.checked)} />
                Same as billing address
              </label>
              {!sameAsBilling && (
                <>
                  <div>
                    <label className="label" htmlFor="ship-name">Full name</label>
                    <input id="ship-name" className="input" required value={shipping.name}
                      onChange={(event) => updateShipping('name', event.target.value)} />
                  </div>
                  <div>
                    <label className="label" htmlFor="ship-line1">Street line 1</label>
                    <input id="ship-line1" className="input" required value={shipping.line1}
                      onChange={(event) => updateShipping('line1', event.target.value)} />
                  </div>
                  <div className="grid gap-4 sm:grid-cols-3">
                    <input className="input" placeholder="City" required value={shipping.city}
                      onChange={(event) => updateShipping('city', event.target.value)} />
                    <input className="input" placeholder="State" required value={shipping.state}
                      onChange={(event) => updateShipping('state', event.target.value)} />
                    <input className="input" placeholder="Zip" required value={shipping.postal_code}
                      onChange={(event) => updateShipping('postal_code', event.target.value)} />
                  </div>
                </>
              )}
              <div className="flex gap-3">
                <button type="button" className="btn-secondary" onClick={() => setStep('payment')}>Back</button>
                <button type="button" className="btn-primary"
                  disabled={!sameAsBilling && (!shipping.name || !shipping.line1 || !shipping.city || !shipping.state || !shipping.postal_code)}
                  onClick={() => setStep('review')}>
                  Review order
                </button>
              </div>
            </>
          )}

          {step === 'review' && (
            <>
              <ul className="divide-y divide-ink-800/10">
                {cart.items.map((line) => (
                  <li key={line.id} className="flex items-center gap-3 py-3">
                    <img src={assetUrl(line.image_url)} alt={line.name} className="h-12 w-12 rounded object-cover" />
                    <span className="flex-1 text-sm">{line.name} × {line.quantity}</span>
                    <span className="text-sm font-medium">{formatMoney(line.line_total_cents)}</span>
                  </li>
                ))}
              </ul>
              <div className="flex gap-3">
                <button type="button" className="btn-secondary" onClick={() => setStep('shipping')}>Back</button>
                <button type="submit" className="btn-primary flex-1" disabled={submitting}>
                  {submitting ? 'Placing order…' : `Pay ${formatMoney(cart.total_cents)}`}
                </button>
              </div>
              <p className="text-xs text-ink-700">
                This is a simulated payment for demo purposes — no real card processor is contacted.
              </p>
            </>
          )}
        </form>
      </section>

      <aside className="card h-fit p-6">
        <h2 className="font-display text-xl text-ink-900">Summary</h2>
        <dl className="mt-4 space-y-2 text-sm">
          <div className="flex justify-between"><dt className="text-ink-700">Subtotal</dt><dd>{formatMoney(cart.subtotal_cents)}</dd></div>
          <div className="flex justify-between"><dt className="text-ink-700">Shipping</dt><dd>{cart.shipping_cents === 0 ? 'Free' : formatMoney(cart.shipping_cents)}</dd></div>
          <div className="flex justify-between"><dt className="text-ink-700">Tax</dt><dd>{formatMoney(cart.tax_cents)}</dd></div>
          <div className="flex justify-between border-t border-ink-800/10 pt-3 text-base font-bold"><dt>Total</dt><dd>{formatMoney(cart.total_cents)}</dd></div>
        </dl>
      </aside>
    </div>
  )
}
