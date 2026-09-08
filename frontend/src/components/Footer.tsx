import { Link } from 'react-router-dom'

/** Site footer with the safety note that belongs on a children's toy store. */
export default function Footer() {
  return (
    <footer className="mt-16 border-t border-ink-800/10 bg-white">
      <div className="mx-auto grid max-w-6xl gap-8 px-4 py-10 sm:grid-cols-3">
        <div>
          <p className="font-display text-lg text-ink-900">ToyBox</p>
          <p className="mt-2 text-sm text-ink-700">
            Toys chosen for how long they last, not how loudly they light up.
          </p>
        </div>
        <div>
          <p className="text-sm font-semibold text-ink-900">Shop</p>
          <ul className="mt-2 space-y-1 text-sm text-ink-700">
            <li>
              <Link to="/catalog" className="hover:text-brand-700">
                All toys
              </Link>
            </li>
            <li>
              <Link to="/catalog?sort=price_asc" className="hover:text-brand-700">
                Best value
              </Link>
            </li>
            <li>
              <Link to="/orders" className="hover:text-brand-700">
                Order history
              </Link>
            </li>
          </ul>
        </div>
        <div>
          <p className="text-sm font-semibold text-ink-900">Safety</p>
          <p className="mt-2 text-sm text-ink-700">
            Every listing carries its manufacturer age range and safety notes. Small parts are a
            choking hazard for children under three — always check the notes before buying.
          </p>
        </div>
      </div>
      <div className="border-t border-ink-800/10 py-4 text-center text-xs text-ink-700">
        © {new Date().getFullYear()} ToyBox. Demo store — payments run in Stripe test mode.
      </div>
    </footer>
  )
}
