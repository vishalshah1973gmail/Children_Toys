import { useCallback, useEffect, useState } from 'react'

import { adminApi } from '../../api/admin'
import { catalogApi } from '../../api/catalog'
import { assetUrl, toApiError } from '../../api/client'
import ErrorBanner from '../../components/ErrorBanner'
import Pagination from '../../components/Pagination'
import Spinner from '../../components/Spinner'
import { formatMoney } from '../../lib/format'
import type { Category, Paged, Product } from '../../types'
import ProductFormModal from './ProductFormModal'

/** Product table with inline stock edits and the create/edit dialog. */
export default function AdminProductsPage() {
  const [result, setResult] = useState<Paged<Product> | null>(null)
  const [categories, setCategories] = useState<Category[]>([])
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [editing, setEditing] = useState<Product | null>(null)
  const [creating, setCreating] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [products, categoryList] = await Promise.all([
        adminApi.products(page, 20, search),
        catalogApi.categories(),
      ])
      setResult(products)
      setCategories(categoryList)
      setError(null)
    } catch (caught) {
      setError(toApiError(caught).message)
    } finally {
      setLoading(false)
    }
  }, [page, search])

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 200)
    return () => window.clearTimeout(timer)
  }, [load])

  async function changeStock(product: Product, delta: number) {
    try {
      await adminApi.adjustStock(product.id, { delta })
      await load()
    } catch (caught) {
      setError(toApiError(caught).message)
    }
  }

  async function removeProduct(product: Product) {
    setError(null)
    try {
      const response = await adminApi.deleteProduct(product.id)
      setError(response.message.includes('deactivated') ? response.message : null)
      await load()
    } catch (caught) {
      setError(toApiError(caught).message)
    }
  }

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <input
          className="input max-w-xs"
          placeholder="Search products…"
          value={search}
          onChange={(event) => {
            setPage(1)
            setSearch(event.target.value)
          }}
        />
        <button
          type="button"
          className="btn-primary ml-auto"
          onClick={() => setCreating(true)}
          disabled={categories.length === 0}
        >
          New product
        </button>
      </div>

      <ErrorBanner message={error} onDismiss={() => setError(null)} />

      {loading && !result ? (
        <Spinner />
      ) : (
        <div className="card overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-ink-800/10 text-xs uppercase tracking-wide text-ink-700">
              <tr>
                <th className="px-4 py-3">Product</th>
                <th className="px-4 py-3">Category</th>
                <th className="px-4 py-3 text-right">Price</th>
                <th className="px-4 py-3 text-center">Stock</th>
                <th className="px-4 py-3">Flags</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-ink-800/5">
              {result?.items.map((product) => (
                <tr key={product.id}>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <img
                        src={assetUrl(product.primary_image_url)}
                        alt=""
                        className="h-10 w-10 rounded object-cover"
                      />
                      <div>
                        <p className="font-medium text-ink-900">{product.name}</p>
                        <p className="text-xs text-ink-700">{product.brand}</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-ink-700">{product.category.name}</td>
                  <td className="px-4 py-3 text-right">{formatMoney(product.price_cents)}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-center gap-2">
                      <button
                        type="button"
                        className="h-7 w-7 rounded border border-ink-800/15 hover:bg-orange-50"
                        onClick={() => void changeStock(product, -1)}
                        aria-label={`Decrease stock for ${product.name}`}
                      >
                        −
                      </button>
                      <span
                        className={`w-10 text-center font-semibold ${
                          product.stock_quantity < 5 ? 'text-red-600' : ''
                        }`}
                      >
                        {product.stock_quantity}
                      </span>
                      <button
                        type="button"
                        className="h-7 w-7 rounded border border-ink-800/15 hover:bg-orange-50"
                        onClick={() => void changeStock(product, 1)}
                        aria-label={`Increase stock for ${product.name}`}
                      >
                        +
                      </button>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-1">
                      {product.is_featured && (
                        <span className="badge bg-orange-100 text-brand-800">featured</span>
                      )}
                      {!product.is_active && (
                        <span className="badge bg-slate-200 text-slate-700">hidden</span>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      type="button"
                      className="text-brand-700 hover:underline"
                      onClick={() => setEditing(product)}
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      className="ml-3 text-red-700 hover:underline"
                      onClick={() => void removeProduct(product)}
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Pagination page={result?.page ?? 1} pages={result?.pages ?? 1} onChange={setPage} />

      {(creating || editing) && (
        <ProductFormModal
          product={editing}
          categories={categories}
          onClose={() => {
            setCreating(false)
            setEditing(null)
          }}
          onSaved={() => {
            setCreating(false)
            setEditing(null)
            void load()
          }}
        />
      )}
    </div>
  )
}
