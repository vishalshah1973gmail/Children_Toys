import { api } from './client'
import type {
  CheckoutSession,
  GuestCheckoutRequestBody,
  GuestCheckoutResponseBody,
  Order,
  Paged,
  ShippingAddressInput,
} from '../types'

export const ordersApi = {
  async list(page = 1, pageSize = 10): Promise<Paged<Order>> {
    const { data } = await api.get<Paged<Order>>('/orders', {
      params: { page, page_size: pageSize },
    })
    return data
  },
  async get(orderNumber: string): Promise<Order> {
    const { data } = await api.get<Order>(`/orders/${orderNumber}`)
    return data
  },
  async createCheckoutSession(
    contactEmail: string,
    address: ShippingAddressInput,
  ): Promise<CheckoutSession> {
    const { data } = await api.post<CheckoutSession>('/checkout/session', {
      contact_email: contactEmail,
      shipping_address: address,
    })
    return data
  },
  async devConfirm(orderNumber: string): Promise<Order> {
    const { data } = await api.post<Order>(`/checkout/dev-confirm/${orderNumber}`)
    return data
  },
  async guestCheckout(body: GuestCheckoutRequestBody): Promise<GuestCheckoutResponseBody> {
    const { data } = await api.post<GuestCheckoutResponseBody>('/checkout/guest', body)
    return data
  },
}
