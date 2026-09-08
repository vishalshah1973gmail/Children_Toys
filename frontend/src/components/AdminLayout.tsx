import { NavLink, Outlet } from 'react-router-dom'

const TABS = [
  { to: '/admin', label: 'Overview', end: true },
  { to: '/admin/products', label: 'Products' },
  { to: '/admin/categories', label: 'Categories' },
  { to: '/admin/orders', label: 'Orders' },
]

/** Chrome around the admin dashboard pages. */
export default function AdminLayout() {
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
          </NavLink>
        ))}
      </nav>

      <Outlet />
    </div>
  )
}
