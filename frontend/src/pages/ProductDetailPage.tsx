import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { catalogApi } from '../api/catalog'
import { assetUrl, toApiError } from '../api/client'
import ErrorBanner from '../components/ErrorBanner'
import Spinner from '../components/Spinner'
import { formatAgeRange, formatMoney } from '../lib/format'
import { useCartStore } from '../store/cartStore'
import type { Product } from '../types'

/** Single product page with image gallery, safety notes and add-to-cart. */
export default function ProductDetailPage() {
  const { slug = '' } = useParams()
  const [product, setProduct] = useState<Product | null>(null)
  const [activeImage, setActiveImage] = useState(0)
  const [quantity, setQuantity] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [added, setAdded] = useState(false)

  const addToCart = useCartStore((state) => state.add)
  const cartError = useCartStore((state) => state.error)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setActiveImage(0)
    setQuantity(1)
    catalogApi
      .product(slug)
      .then((data) => {
        if (!cancelled) {
          setProduct(data)
          setError(null)
        }
      })
      .catch((caught) => {
        if (!cancelled) setError(toApiError(caught).message)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [slug])

  async function handleAdd() {
    if (!product) return
    await addToCart(product, quantity)
    setAdded(true)
    window.setTimeout(() => setAdded(false), 2500)
  }

  if (loading) return <Spinner label="Fetching this toy…" />
  if (error || !product) {
    return (
      <div className="py-16 text-center">
        <ErrorBanner message={error ?? 'Product not found'} />
        <Link to="/catalog" className="btn-primary mt-4">
          Back to the catalog
        </Link>
      </div>
    )
  }

  const images = product.images.length > 0 ? product.images : []
  const soldOut = product.stock_quantity <= 0

  return (
    <div>
      <nav className="mb-5 text-sm text-ink-700">
        <Link to="/catalog" className="hover:text-brand-700">
          Catalog
        </Link>
        <span className="px-2">/</span>
        <Link to={`/catalog?category=${product.category.slug}`} className="hover:text-brand-700">
          {product.category.name}
        </Link>
      </nav>

      <div className="grid gap-8 lg:grid-cols-2">
        <div>
          <div className="card overflow-hidden bg-orange-50">
            <img
              src={assetUrl(images[activeImage]?.url ?? product.primary_image_url)}
              alt={images[activeImage]?.alt_text ?? product.name}
              className="h-[420px] w-full object-cover"
            />
          </div>
          {images.length > 1 && (
            <div className="mt-3 flex gap-2">
              {images.map((image, index) => (
                <button
                  key={image.id}
                  type="button"
                  onClick={() => setActiveImage(index)}
                  className={`h-20 w-20 overflow-hidden rounded-lg border-2 ${
                    index === activeImage ? 'border-brand-500' : 'border-transparent'
                  }`}
                >
                  <img
                    src={assetUrl(image.url)}
                    alt={image.alt_text ?? ''}
                    className="h-full w-full object-cover"
                  />
                </button>
              ))}
            </div>
          )}
        </div>

        <div>
          <p className="badge bg-orange-100 text-brand-800">{product.brand}</p>
          <h1 className="mt-3 font-display text-3xl text-ink-900">{product.name}</h1>
          <p className="mt-2 text-2xl font-semibold text-ink-900">
            {formatMoney(product.price_cents)}
          </p>

          <dl className="mt-5 grid grid-cols-2 gap-3 text-sm">
            <div className="rounded-lg bg-white p-3">
              <dt className="text-ink-700">Recommended age</dt>
              <dd className="font-semibold text-ink-900">
                {formatAgeRange(product.min_age_months, product.max_age_months)}
              </dd>
            </div>
            <div className="rounded-lg bg-white p-3">
              <dt className="text-ink-700">Availability</dt>
              <dd className={`font-semibold ${soldOut ? 'text-red-600' : 'text-emerald-700'}`}>
                {soldOut ? 'Sold out' : `${product.stock_quantity} in stock`}
              </dd>
            </div>
          </dl>

          <p className="mt-5 leading-relaxed text-ink-700">{product.description}</p>

          {product.safety_notes && (
            <div className="mt-5 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
              <p className="font-semibold">Safety notes</p>
              <p className="mt-1">{product.safety_notes}</p>
            </div>
          )}

          <ErrorBanner message={cartError} />

          <div className="mt-6 flex items-center gap-3">
            <label className="text-sm text-ink-700" htmlFor="quantity">
              Qty
            </label>
            <input
              id="quantity"
              type="number"
              min={1}
              max={Math.max(product.stock_quantity, 1)}
              value={quantity}
              onChange={(event) => setQuantity(Math.max(1, Number(event.target.value)))}
              className="input w-24"
              disabled={soldOut}
            />
            <button
              type="button"
              className="btn-primary flex-1"
              disabled={soldOut}
              onClick={() => void handleAdd()}
            >
              {soldOut ? 'Sold out' : 'Add to cart'}
            </button>
          </div>

          {added && (
            <p className="mt-3 text-sm font-semibold text-emerald-700">
              Added to your cart. <Link to="/cart" className="underline">View cart</Link>
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
