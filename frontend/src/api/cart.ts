import { api } from './client'
import type { Cart } from '../types'

export const cartApi = {
  async get(): Promise<Cart> {
    const { data } = await api.get<Cart>('/cart')
    return data
  },
  async add(productId: number, quantity = 1): Promise<Cart> {
    const { data } = await api.post<Cart>('/cart/items', { product_id: productId, quantity })
    return data
  },
  async update(itemId: number, quantity: number): Promise<Cart> {
    const { data } = await api.patch<Cart>(`/cart/items/${itemId}`, { quantity })
    return data
  },
  async remove(itemId: number): Promise<Cart> {
    const { data } = await api.delete<Cart>(`/cart/items/${itemId}`)
    return data
  },
  async clear(): Promise<Cart> {
    const { data } = await api.delete<Cart>('/cart')
    return data
  },
  async merge(items: { product_id: number; quantity: number }[]): Promise<Cart> {
    const { data } = await api.post<Cart>('/cart/merge', { items })
    return data
  },
}
