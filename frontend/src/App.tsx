import { useEffect } from 'react'
import { Route, Routes } from 'react-router-dom'

import AdminLayout from './components/AdminLayout'
import AdminRoute from './components/AdminRoute'
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import AccountPage from './pages/AccountPage'
import CartPage from './pages/CartPage'
import CatalogPage from './pages/CatalogPage'
import CheckoutCancelPage from './pages/CheckoutCancelPage'
import CheckoutPage from './pages/CheckoutPage'
import CheckoutSuccessPage from './pages/CheckoutSuccessPage'
import GuestCheckoutPage from './pages/GuestCheckoutPage'
import HomePage from './pages/HomePage'
import LoginPage from './pages/LoginPage'
import NotFoundPage from './pages/NotFoundPage'
import OrderDetailPage from './pages/OrderDetailPage'
import OrdersPage from './pages/OrdersPage'
import ProductDetailPage from './pages/ProductDetailPage'
import RegisterPage from './pages/RegisterPage'
import AdminCategoriesPage from './pages/admin/AdminCategoriesPage'
import AdminOrdersPage from './pages/admin/AdminOrdersPage'
import AdminOverviewPage from './pages/admin/AdminOverviewPage'
import AdminProductsPage from './pages/admin/AdminProductsPage'
import { useAuthStore } from './store/authStore'
import { useCartStore } from './store/cartStore'

/** Route table plus the one-time session/cart bootstrap. */
export default function App() {
  const bootstrap = useAuthStore((state) => state.bootstrap)
  const user = useAuthStore((state) => state.user)
  const initialised = useAuthStore((state) => state.initialised)
  const setAuthenticated = useCartStore((state) => state.setAuthenticated)
  const refreshCart = useCartStore((state) => state.refresh)

  useEffect(() => {
    void bootstrap()
  }, [bootstrap])

  useEffect(() => {
    if (!initialised) return
    setAuthenticated(Boolean(user))
    void refreshCart()
  }, [initialised, user, setAuthenticated, refreshCart])

  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<HomePage />} />
        <Route path="catalog" element={<CatalogPage />} />
        <Route path="product/:slug" element={<ProductDetailPage />} />
        <Route path="cart" element={<CartPage />} />
        <Route path="login" element={<LoginPage />} />
        <Route path="register" element={<RegisterPage />} />
        <Route path="checkout/cancel" element={<CheckoutCancelPage />} />
        <Route path="checkout/guest" element={<GuestCheckoutPage />} />

        <Route element={<ProtectedRoute />}>
          <Route path="checkout" element={<CheckoutPage />} />
          <Route path="checkout/success" element={<CheckoutSuccessPage />} />
          <Route path="orders" element={<OrdersPage />} />
          <Route path="orders/:orderNumber" element={<OrderDetailPage />} />
          <Route path="account" element={<AccountPage />} />
        </Route>

        <Route element={<AdminRoute />}>
          <Route path="admin" element={<AdminLayout />}>
            <Route index element={<AdminOverviewPage />} />
            <Route path="products" element={<AdminProductsPage />} />
            <Route path="categories" element={<AdminCategoriesPage />} />
            <Route path="orders" element={<AdminOrdersPage />} />
          </Route>
        </Route>

        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}
