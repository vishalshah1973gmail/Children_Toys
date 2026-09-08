import { useCallback, useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'

import { catalogApi } from '../api/catalog'
import { toApiError } from '../api/client'
import CatalogFilters, { type FilterValues } from '../components/CatalogFilters'
import EmptyState from '../components/EmptyState'
import ErrorBanner from '../components/ErrorBanner'
import Pagination from '../components/Pagination'
import ProductCard from '../components/ProductCard'
import Spinner from '../components/Spinner'
import { useCartStore } from '../store/cartStore'
import type { Category, Paged, Product } from '../types'

const PAGE_SIZE = 12

const SORT_OPTIONS = [
  { value: 'newest', label: 'Newest first' },
  { value: 'price_asc', label: 'Price: low to high' },
  { value: 'price_desc', label: 'Price: high to low' },
  { value: 'name_asc', label: 'Name: A–Z' },
  { value: 'name_desc', label: 'Name: Z–A' },
]

/** Catalog with filters, keyword search, sorting and pagination in the URL. */
export default function CatalogPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [result, setResult] = useState<Paged<Product> | null>(null)
  const [categories, setCategories] = useState<Category[]>([])
  const [brands, setBrands] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const addToCart = useCartStore((state) => state.add)
  const cartError = useCartStore((state) => state.error)

  const values: FilterValues = useMemo(
    () => ({
      q: searchParams.get('q') ?? '',
      category: searchParams.get('category') ?? '',
      ageMonths: searchParams.get('age_months') ?? '',
      minPrice: searchParams.get('min_price') ?? '',
      maxPrice: searchParams.get('max_price') ?? '',
      brand: searchParams.get('brand') ?? '',
      inStock: searchParams.get('in_stock') === '1',
      sort: searchParams.get('sort') ?? 'newest',
    }),
    [searchParams],
  )
  const page = Number(searchParams.get('page') ?? '1')

  const updateParams = useCallback(
    (patch: Partial<FilterValues> & { page?: number }) => {
      const next = new URLSearchParams(searchParams)
      const mapping: Record<string, string> = {
        q: 'q',
        category: 'category',
        ageMonths: 'age_months',
        minPrice: 'min_price',
        maxPrice: 'max_price',
        brand: 'brand',
        sort: 'sort',
      }
      Object.entries(patch).forEach(([key, value]) => {
        if (key === 'inStock') {
          if (value) next.set('in_stock', '1')
          else next.delete('in_stock')
          return
        }
        if (key === 'page') {
          next.set('page', String(value))
          return
        }
        const param = mapping[key]
        if (!param) return
        if (value === '' || value === undefined) next.delete(param)
        else next.set(param, String(value))
      })
      if (!('page' in patch)) next.set('page', '1')
      setSearchParams(next, { replace: true })
    },
    [searchParams, setSearchParams],
  )

  useEffect(() => {
    let cancelled = false
    async function loadFacets() {
      try {
        const [categoryList, brandList] = await Promise.all([
          catalogApi.categories(),
          catalogApi.brands(),
        ])
        if (cancelled) return
        setCategories(categoryList)
        setBrands(brandList)
      } catch {
        // Filters degrade to text search if the facets fail.
      }
    }
    void loadFacets()
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    const timer = window.setTimeout(async () => {
      setLoading(true)
      try {
        const data = await catalogApi.products({
          q: values.q || undefined,
          category: values.category || undefined,
          age_months: values.ageMonths ? Number(values.ageMonths) : undefined,
          min_price_cents: values.minPrice ? Math.round(Number(values.minPrice) * 100) : undefined,
          max_price_cents: values.maxPrice ? Math.round(Number(values.maxPrice) * 100) : undefined,
          brand: values.brand || undefined,
          in_stock: values.inStock || undefined,
          sort: values.sort as never,
          page,
          page_size: PAGE_SIZE,
        })
        if (!cancelled) {
          setResult(data)
          setError(null)
        }
      } catch (caught) {
        if (!cancelled) setError(toApiError(caught).message)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }, 250)

    return () => {
      cancelled = true
      window.clearTimeout(timer)
    }
  }, [values, page])

  return (
    <div className="grid gap-8 lg:grid-cols-[260px_1fr]">
      <CatalogFilters
        values={values}
        categories={categories}
        brands={brands}
        onChange={updateParams}
        onReset={() => setSearchParams(new URLSearchParams(), { replace: true })}
      />

      <section>
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="font-display text-2xl text-ink-900">All toys</h1>
            <p className="text-sm text-ink-700">
              {result ? `${result.total} toys match your filters` : 'Loading the shelves…'}
            </p>
          </div>
          <label className="flex items-center gap-2 text-sm text-ink-700">
            Sort
            <select
              className="input w-52"
              value={values.sort}
              onChange={(event) => updateParams({ sort: event.target.value })}
            >
              {SORT_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
        </div>

        <ErrorBanner message={error ?? cartError} />

        {loading && !result ? (
          <Spinner />
        ) : result && result.items.length === 0 ? (
          <EmptyState
            title="Nothing matches those filters"
            description="Try widening the age band or clearing the price range."
          />
        ) : (
          <>
            <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
              {result?.items.map((product) => (
                <ProductCard
                  key={product.id}
                  product={product}
                  onAdd={(item) => void addToCart(item)}
                />
              ))}
            </div>
            <Pagination
              page={result?.page ?? 1}
              pages={result?.pages ?? 1}
              onChange={(next) => updateParams({ page: next })}
            />
          </>
        )}
      </section>
    </div>
  )
}
