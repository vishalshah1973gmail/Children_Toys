import { useCallback, useEffect, useRef, useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router-dom'

import { adminApi } from '../api/admin'

const TABS = [
  { to: '/admin', label: 'Overview', end: true },
  { to: '/admin/approvals', label: 'Approvals' },
  { to: '/admin/products', label: 'Products' },
  { to: '/admin/categories', label: 'Categories' },
  { to: '/admin/orders', label: 'Orders' },
]

/** Context AdminLayout hands to its routed pages through <Outlet context={{ refreshPending } satisfies AdminOutletContext} />. */
export type AdminOutletContext = { refreshPending: () => void }

/** Chrome around the admin dashboard pages. */
export default function AdminLayout() {
  const [pending, setPending] = useState(0)
  const location = useLocation()

  const latestRequest = useRef(0)

  const refreshPending = useCallback(() => {
    const requestId = ++latestRequest.current
    adminApi
      .stats()
      .then((stats) => {
        if (requestId === latestRequest.current) setPending(stats.pending_approvals)
      })
      .catch(() => {})
  }, [])

  useEffect(() => {
    refreshPending()
  }, [location.pathname, refreshPending])

  useEffect(() => {
    return () => {
      latestRequest.current = -1
    }
  }, [])

  return (
    <div>
      <div className="mb-6">
        <h1 className="font-display text-3xl text-ink-900">Admin dashboard</h1>
        <p className="text-sm text-ink-700">
          Catalogue, stock and order fulfilment. All actions are re-checked server-side.
        </p>
      </div>

      <nav className="mb-6 flex flex-wrap gap-2 border-b border-ink-800/10 pb-3">
        {TABS.map((tab) => (
          <NavLink
            key={tab.to}
            to={tab.to}
            end={tab.end}
            className={({ isActive }) =>
              `rounded-lg px-3 py-2 text-sm font-medium ${
                isActive ? 'bg-ink-900 text-white' : 'text-ink-700 hover:bg-orange-100'
              }`
            }
          >
            {tab.label}
            {tab.to === '/admin/approvals' && pending > 0 && (
              <span className="ml-2 rounded-full bg-red-600 px-2 py-0.5 text-xs font-bold text-white">
                {pending}
              </span>
            )}
          </NavLink>
        ))}
      </nav>

      <Outlet context={{ refreshPending } satisfies AdminOutletContext} />
    </div>
  )
}
