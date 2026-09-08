import { api } from './client'
import type { CatalogQuery, Category, Paged, Product } from '../types'

export const catalogApi = {
  async categories(): Promise<Category[]> {
    const { data } = await api.get<Category[]>('/categories')
    return data
  },
  async products(query: CatalogQuery = {}): Promise<Paged<Product>> {
    const params = Object.fromEntries(
      Object.entries(query).filter(([, value]) => value !== undefined && value !== '' && value !== null),
    )
    const { data } = await api.get<Paged<Product>>('/products', { params })
    return data
  },
  async featured(limit = 8): Promise<Product[]> {
    const { data } = await api.get<Product[]>('/products/featured', { params: { limit } })
    return data
  },
  async brands(): Promise<string[]> {
    const { data } = await api.get<string[]>('/products/brands')
    return data
  },
  async product(slug: string): Promise<Product> {
    const { data } = await api.get<Product>(`/products/${slug}`)
    return data
  },
}
