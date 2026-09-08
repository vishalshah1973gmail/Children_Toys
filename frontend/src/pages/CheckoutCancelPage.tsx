import { Link, useSearchParams } from 'react-router-dom'

/** Stripe sends the shopper here when they abandon the payment page. */
export default function CheckoutCancelPage() {
  const [searchParams] = useSearchParams()
  const orderNumber = searchParams.get('order_number')

  return (
    <div className="mx-auto max-w-xl py-16 text-center">
      <h1 className="font-display text-3xl text-ink-900">Payment cancelled</h1>
      <p className="mt-3 text-ink-700">
        Nothing has been charged and your cart is untouched.
        {orderNumber && (
          <>
            {' '}
            Order <span className="font-semibold">{orderNumber}</span> stays pending until it is
            paid.
          </>
        )}
      </p>
      <div className="mt-6 flex justify-center gap-3">
        <Link to="/cart" className="btn-primary">
          Back to cart
        </Link>
        <Link to="/catalog" className="btn-secondary">
          Keep shopping
        </Link>
      </div>
    </div>
  )
}
