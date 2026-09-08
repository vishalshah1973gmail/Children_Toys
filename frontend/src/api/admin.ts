import { api } from './client'
import type { AdminStats, Category, Order, OrderStatus, Paged, Product } from '../types'

export interface ProductPayload {
  name: string
  description: string
  price_cents: number
  stock_quantity: number
  category_id: number
  min_age_months: number
  max_age_months: number
  brand: string
  safety_notes?: string | null
  is_featured: boolean
  is_active: boolean
  images?: { url: string; alt_text?: string | null; sort_order?: number; is_primary?: boolean }[]
}

export const adminApi = {
  async stats(): Promise<AdminStats> {
    const { data } = await api.get<AdminStats>('/admin/stats')
    return data
  },
  async products(page = 1, pageSize = 20, q?: string): Promise<Paged<Product>> {
    const { data } = await api.get<Paged<Product>>('/admin/products', {
      params: { page, page_size: pageSize, q: q || undefined },
    })
    return data
  },
  async createProduct(payload: ProductPayload): Promise<Product> {
    const { data } = await api.post<Product>('/admin/products', payload)
    return data
  },
  async updateProduct(id: number, payload: Partial<ProductPayload>): Promise<Product> {
    const { data } = await api.patch<Product>(`/admin/products/${id}`, payload)
    return data
  },
  async adjustStock(id: number, change: { set_to?: number; delta?: number }): Promise<Product> {
    const { data } = await api.patch<Product>(`/admin/products/${id}/stock`, change)
    return data
  },
  async deleteProduct(id: number): Promise<{ message: string }> {
    const { data } = await api.delete<{ message: string }>(`/admin/products/${id}`)
    return data
  },
  async createCategory(payload: {
    name: string
    description?: string | null
    image_url?: string | null
  }): Promise<Category> {
    const { data } = await api.post<Category>('/admin/categories', payload)
    return data
  },
  async updateCategory(
    id: number,
    payload: { name?: string; description?: string | null },
  ): Promise<Category> {
    const { data } = await api.patch<Category>(`/admin/categories/${id}`, payload)
    return data
  },
  async deleteCategory(id: number): Promise<{ message: string }> {
    const { data } = await api.delete<{ message: string }>(`/admin/categories/${id}`)
    return data
  },
  async uploadImage(file: File): Promise<{ url: string; filename: string; size_bytes: number }> {
    const form = new FormData()
    form.append('file', file)
    const { data } = await api.post('/admin/uploads/images', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data
  },
  async orders(page = 1, pageSize = 20, status?: OrderStatus): Promise<Paged<Order>> {
    const { data } = await api.get<Paged<Order>>('/admin/orders', {
      params: { page, page_size: pageSize, status: status || undefined },
    })
    return data
  },
  async setOrderStatus(orderNumber: string, status: OrderStatus): Promise<Order> {
    const { data } = await api.patch<Order>(`/admin/orders/${orderNumber}/status`, { status })
    return data
  },
}
