import { type FormEvent, useState } from 'react'

import { adminApi, type ProductPayload } from '../../api/admin'
import { assetUrl, toApiError } from '../../api/client'
import ErrorBanner from '../../components/ErrorBanner'
import type { Category, Product } from '../../types'

interface ProductFormModalProps {
  product: Product | null
  categories: Category[]
  onClose: () => void
  onSaved: () => void
}

function emptyForm(categories: Category[]) {
  return {
    name: '',
    description: '',
    price: '0.00',
    stock_quantity: 0,
    category_id: categories[0]?.id ?? 0,
    min_age_months: 36,
    max_age_months: 96,
    brand: '',
    safety_notes: '',
    is_featured: false,
    is_active: true,
  }
}

/** Create / edit dialog for a product, including image upload. */
export default function ProductFormModal({
  product,
  categories,
  onClose,
  onSaved,
}: ProductFormModalProps) {
  const [form, setForm] = useState(
    product
      ? {
          name: product.name,
          description: product.description,
          price: (product.price_cents / 100).toFixed(2),
          stock_quantity: product.stock_quantity,
          category_id: product.category_id,
          min_age_months: product.min_age_months,
          max_age_months: product.max_age_months,
          brand: product.brand,
          safety_notes: product.safety_notes ?? '',
          is_featured: product.is_featured,
          is_active: product.is_active,
        }
      : emptyForm(categories),
  )
  const [images, setImages] = useState<string[]>(product?.images.map((image) => image.url) ?? [])
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [uploading, setUploading] = useState(false)

  function update<K extends keyof typeof form>(field: K, value: (typeof form)[K]) {
    setForm((current) => ({ ...current, [field]: value }))
  }

  async function handleUpload(file: File | undefined) {
    if (!file) return
    setUploading(true)
    setError(null)
    try {
      const uploaded = await adminApi.uploadImage(file)
      setImages((current) => [...current, uploaded.url])
    } catch (caught) {
      setError(toApiError(caught).message)
    } finally {
      setUploading(false)
    }
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setSaving(true)
    setError(null)

    const payload: ProductPayload = {
      name: form.name,
      description: form.description,
      // Money is entered in dollars and sent as integer cents.
      price_cents: Math.round(Number(form.price) * 100),
      stock_quantity: Number(form.stock_quantity),
      category_id: Number(form.category_id),
      min_age_months: Number(form.min_age_months),
      max_age_months: Number(form.max_age_months),
      brand: form.brand,
      safety_notes: form.safety_notes || null,
      is_featured: form.is_featured,
      is_active: form.is_active,
      images: images.map((url, index) => ({
        url,
        alt_text: form.name,
        sort_order: index,
        is_primary: index === 0,
      })),
    }

    try {
      if (product) await adminApi.updateProduct(product.id, payload)
      else await adminApi.createProduct(payload)
      onSaved()
    } catch (caught) {
      setError(toApiError(caught).message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="fixed inset-0 z-40 grid place-items-center bg-ink-900/40 p-4">
      <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-xl bg-white p-6 shadow-xl">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="font-display text-xl text-ink-900">
            {product ? `Edit ${product.name}` : 'New product'}
          </h2>
          <button type="button" className="btn-ghost" onClick={onClose}>
            Close
          </button>
        </div>

        <ErrorBanner message={error} onDismiss={() => setError(null)} />

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="sm:col-span-2">
              <label className="label" htmlFor="p-name">
                Name
              </label>
              <input
                id="p-name"
                className="input"
                required
                minLength={2}
                value={form.name}
                onChange={(event) => update('name', event.target.value)}
              />
            </div>

            <div className="sm:col-span-2">
              <label className="label" htmlFor="p-description">
                Description
              </label>
              <textarea
                id="p-description"
                className="input h-28"
                value={form.description}
                onChange={(event) => update('description', event.target.value)}
              />
            </div>

            <div>
              <label className="label" htmlFor="p-price">
                Price (USD)
              </label>
              <input
                id="p-price"
                type="number"
                step="0.01"
                min="0"
                className="input"
                required
                value={form.price}
                onChange={(event) => update('price', event.target.value)}
              />
            </div>

            <div>
              <label className="label" htmlFor="p-stock">
                Stock
              </label>
              <input
                id="p-stock"
                type="number"
                min={0}
                className="input"
                required
                value={form.stock_quantity}
                onChange={(event) => update('stock_quantity', Number(event.target.value))}
              />
            </div>

            <div>
              <label className="label" htmlFor="p-category">
                Category
              </label>
              <select
                id="p-category"
                className="input"
                value={form.category_id}
                onChange={(event) => update('category_id', Number(event.target.value))}
              >
                {categories.map((category) => (
                  <option key={category.id} value={category.id}>
                    {category.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="label" htmlFor="p-brand">
                Brand
              </label>
              <input
                id="p-brand"
                className="input"
                required
                value={form.brand}
                onChange={(event) => update('brand', event.target.value)}
              />
            </div>

            <div>
              <label className="label" htmlFor="p-min-age">
                Min age (months)
              </label>
              <input
                id="p-min-age"
                type="number"
                min={0}
                max={240}
                className="input"
                value={form.min_age_months}
                onChange={(event) => update('min_age_months', Number(event.target.value))}
              />
            </div>

            <div>
              <label className="label" htmlFor="p-max-age">
                Max age (months)
              </label>
              <input
                id="p-max-age"
                type="number"
                min={0}
                max={240}
                className="input"
                value={form.max_age_months}
                onChange={(event) => update('max_age_months', Number(event.target.value))}
              />
            </div>

            <div className="sm:col-span-2">
              <label className="label" htmlFor="p-safety">
                Safety notes
              </label>
              <textarea
                id="p-safety"
                className="input h-20"
                value={form.safety_notes}
                onChange={(event) => update('safety_notes', event.target.value)}
              />
            </div>
          </div>

          <div>
            <span className="label">Images</span>
            <div className="flex flex-wrap items-center gap-3">
              {images.map((url) => (
                <div key={url} className="relative">
                  <img
                    src={assetUrl(url)}
                    alt=""
                    className="h-20 w-20 rounded-lg border border-ink-800/10 object-cover"
                  />
                  <button
                    type="button"
                    className="absolute -right-2 -top-2 grid h-6 w-6 place-items-center rounded-full bg-red-600 text-xs text-white"
                    onClick={() => setImages((current) => current.filter((item) => item !== url))}
                    aria-label="Remove image"
                  >
                    ×
                  </button>
                </div>
              ))}
              <label className="btn-secondary cursor-pointer">
                {uploading ? 'Uploading…' : 'Upload image'}
                <input
                  type="file"
                  accept="image/png,image/jpeg,image/webp,image/gif"
                  className="hidden"
                  onChange={(event) => void handleUpload(event.target.files?.[0])}
                />
              </label>
            </div>
            <p className="mt-1 text-xs text-ink-700">
              The first image becomes the primary. Files are stored on the backend's local disk.
            </p>
          </div>

          <div className="flex gap-6">
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={form.is_featured}
                onChange={(event) => update('is_featured', event.target.checked)}
              />
              Featured on the home page
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={form.is_active}
                onChange={(event) => update('is_active', event.target.checked)}
              />
              Visible in the storefront
            </label>
          </div>

          <div className="flex justify-end gap-3 border-t border-ink-800/10 pt-4">
            <button type="button" className="btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={saving}>
              {saving ? 'Saving…' : product ? 'Save changes' : 'Create product'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
