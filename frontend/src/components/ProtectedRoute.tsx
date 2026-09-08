import { Navigate, Outlet, useLocation } from 'react-router-dom'

import { useAuthStore } from '../store/authStore'
import Spinner from './Spinner'

/** Requires any signed-in user. */
export default function ProtectedRoute() {
  const user = useAuthStore((state) => state.user)
  const initialised = useAuthStore((state) => state.initialised)
  const location = useLocation()

  if (!initialised) return <Spinner label="Checking your session…" />
  if (!user) return <Navigate to="/login" state={{ from: location.pathname }} replace />
  return <Outlet />
}
