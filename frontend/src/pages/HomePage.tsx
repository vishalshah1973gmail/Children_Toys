import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import { catalogApi } from '../api/catalog'
import { assetUrl, toApiError } from '../api/client'
import ErrorBanner from '../components/ErrorBanner'
import ProductCard from '../components/ProductCard'
import Spinner from '../components/Spinner'
import { useCartStore } from '../store/cartStore'
import type { Category, Product } from '../types'

/** Landing page: hero, categories and featured toys. */
export default function HomePage() {
  const [featured, setFeatured] = useState<Product[]>([])
  const [categories, setCategories] = useState<Category[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const addToCart = useCartStore((state) => state.add)

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        const [featuredProducts, categoryList] = await Promise.all([
          catalogApi.featured(8),
          catalogApi.categories(),
        ])
        if (cancelled) return
        setFeatured(featuredProducts)
        setCategories(categoryList)
      } catch (caught) {
        if (!cancelled) setError(toApiError(caught).message)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <div className="space-y-14">
      <section className="card overflow-hidden">
        <div className="grid gap-6 p-8 sm:p-12 md:grid-cols-[1.2fr_1fr] md:items-center">
          <div>
            <p className="badge bg-orange-100 text-brand-800">Ages 0–14</p>
            <h1 className="mt-3 font-display text-4xl leading-tight text-ink-900 sm:text-5xl">
              Toys worth keeping.
            </h1>
            <p className="mt-4 max-w-lg text-ink-700">
              Every toy here lists its real age range, its brand and its safety notes — so you can
              buy for the child in front of you rather than the box art.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <Link to="/catalog" className="btn-primary">
                Shop all toys
              </Link>
              <Link to="/catalog?age_months=48" className="btn-secondary">
                Find by age
              </Link>
            </div>
          </div>
          <div className="grid grid-cols-3 gap-3">
            {featured.slice(0, 6).map((product) => (
              <Link
                key={product.id}
                to={`/product/${product.slug}`}
                className="aspect-square overflow-hidden rounded-xl bg-orange-50"
              >
                <img
                  src={assetUrl(product.primary_image_url)}
                  alt={product.name}
                  className="h-full w-full object-cover"
                />
              </Link>
            ))}
          </div>
        </div>
      </section>

      <ErrorBanner message={error} onDismiss={() => setError(null)} />

      <section>
        <h2 className="font-display text-2xl text-ink-900">Shop by category</h2>
        <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          {categories.map((category) => (
            <Link
              key={category.id}
              to={`/catalog?category=${category.slug}`}
              className="card p-5 transition hover:-translate-y-0.5 hover:shadow-md"
            >
              <p className="font-display text-lg text-ink-900">{category.name}</p>
              <p className="mt-1 line-clamp-2 text-sm text-ink-700">{category.description}</p>
              <p className="mt-3 text-xs font-semibold text-brand-700">
                {category.product_count} toys
              </p>
            </Link>
          ))}
        </div>
      </section>

      <section>
        <div className="flex items-end justify-between">
          <h2 className="font-display text-2xl text-ink-900">This month's favourites</h2>
          <Link to="/catalog" className="text-sm font-semibold text-brand-700 hover:underline">
            See everything →
          </Link>
        </div>

        {loading ? (
          <Spinner />
        ) : (
          <div className="mt-4 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {featured.map((product) => (
              <ProductCard key={product.id} product={product} onAdd={(item) => void addToCart(item)} />
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
