import { Link } from 'react-router-dom'

/** 404 route. */
export default function NotFoundPage() {
  return (
    <div className="py-20 text-center">
      <p className="font-display text-6xl text-brand-600">404</p>
      <h1 className="mt-3 font-display text-2xl text-ink-900">That shelf is empty</h1>
      <p className="mt-2 text-sm text-ink-700">
        The page you were looking for has been packed away.
      </p>
      <Link to="/catalog" className="btn-primary mt-6">
        Browse the toys
      </Link>
    </div>
  )
}
