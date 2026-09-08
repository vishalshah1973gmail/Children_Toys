import { Navigate, Outlet, useLocation } from 'react-router-dom'

import { useAuthStore } from '../store/authStore'
import Spinner from './Spinner'

/**
 * Requires an admin. The backend enforces this too — this only keeps the UI
 * honest; every admin API call is checked server-side by role.
 */
export default function AdminRoute() {
  const user = useAuthStore((state) => state.user)
  const initialised = useAuthStore((state) => state.initialised)
  const location = useLocation()

  if (!initialised) return <Spinner label="Checking your session…" />
  if (!user) return <Navigate to="/login" state={{ from: location.pathname }} replace />
  if (user.role !== 'admin') return <Navigate to="/" replace />
  return <Outlet />
}
