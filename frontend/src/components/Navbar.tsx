import { useState } from 'react'
import { Link, NavLink, useNavigate } from 'react-router-dom'

import { useAuthStore } from '../store/authStore'
import { useCartStore } from '../store/cartStore'

const NAV_LINKS = [
  { to: '/', label: 'Home', end: true },
  { to: '/catalog', label: 'Shop all' },
  { to: '/catalog?category=stem-learning', label: 'STEM' },
  { to: '/catalog?category=outdoor-active-play', label: 'Outdoor' },
]

/** Top navigation with cart count and the account menu. */
export default function Navbar() {
  const user = useAuthStore((state) => state.user)
  const logout = useAuthStore((state) => state.logout)
  const itemCount = useCartStore((state) => state.cart.item_count)
  const setAuthenticated = useCartStore((state) => state.setAuthenticated)
  const loadGuestCart = useCartStore((state) => state.loadGuestCart)
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)

  async function handleLogout() {
    await logout()
    setAuthenticated(false)
    loadGuestCart()
    setMenuOpen(false)
    navigate('/')
  }

  return (
    <header className="sticky top-0 z-30 border-b border-ink-800/10 bg-white/95 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center gap-6 px-4 py-3">
        <Link to="/" className="flex items-center gap-2">
          <span className="grid h-9 w-9 place-items-center rounded-lg bg-brand-600 font-display text-lg text-white">
            T
          </span>
          <span className="font-display text-xl text-ink-900">ToyBox</span>
        </Link>

        <nav className="hidden items-center gap-1 md:flex">
          {NAV_LINKS.map((link) => (
            <NavLink
              key={link.label}
              to={link.to}
              end={link.end}
              className={({ isActive }) =>
                `rounded-lg px-3 py-2 text-sm font-medium ${
                  isActive ? 'bg-orange-100 text-brand-800' : 'text-ink-700 hover:bg-orange-50'
                }`
              }
            >
              {link.label}
            </NavLink>
          ))}
        </nav>

        <div className="ml-auto flex items-center gap-2">
          <Link to="/cart" className="btn-ghost relative" aria-label="Cart">
            Cart
            {itemCount > 0 && (
              <span className="grid h-5 min-w-5 place-items-center rounded-full bg-brand-600 px-1.5 text-xs font-bold text-white">
                {itemCount}
              </span>
            )}
          </Link>

          {user ? (
            <div className="relative">
              <button
                type="button"
                className="btn-secondary"
                onClick={() => setMenuOpen((open) => !open)}
                aria-expanded={menuOpen}
                aria-haspopup="menu"
              >
                {user.username}
              </button>
              {menuOpen && (
                <div
                  role="menu"
                  className="absolute right-0 mt-2 w-48 overflow-hidden rounded-lg border border-ink-800/10 bg-white py-1 shadow-lg"
                >
                  <Link
                    to="/orders"
                    role="menuitem"
                    className="block px-4 py-2 text-sm hover:bg-orange-50"
                    onClick={() => setMenuOpen(false)}
                  >
                    My orders
                  </Link>
                  <Link
                    to="/account"
                    role="menuitem"
                    className="block px-4 py-2 text-sm hover:bg-orange-50"
                    onClick={() => setMenuOpen(false)}
                  >
                    Account
                  </Link>
                  {user.role === 'admin' && (
                    <Link
                      to="/admin"
                      role="menuitem"
                      className="block px-4 py-2 text-sm font-semibold text-brand-700 hover:bg-orange-50"
                      onClick={() => setMenuOpen(false)}
                    >
                      Admin dashboard
                    </Link>
                  )}
                  <button
                    type="button"
                    role="menuitem"
                    onClick={handleLogout}
                    className="w-full px-4 py-2 text-left text-sm text-red-700 hover:bg-red-50"
                  >
                    Sign out
                  </button>
                </div>
              )}
            </div>
          ) : (
            <>
              <Link to="/login" className="btn-ghost">
                Sign in
              </Link>
              <Link to="/register" className="btn-primary">
                Create account
              </Link>
            </>
          )}
        </div>
      </div>
    </header>
  )
}
