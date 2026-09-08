import type { Category } from '../types'

export interface FilterValues {
  q: string
  category: string
  ageMonths: string
  minPrice: string
  maxPrice: string
  brand: string
  inStock: boolean
  sort: string
}

interface CatalogFiltersProps {
  values: FilterValues
  categories: Category[]
  brands: string[]
  onChange: (patch: Partial<FilterValues>) => void
  onReset: () => void
}

const AGE_BANDS = [
  { label: 'Any age', value: '' },
  { label: '0–18 months', value: '12' },
  { label: '18 months–3 years', value: '30' },
  { label: '3–5 years', value: '48' },
  { label: '5–8 years', value: '78' },
  { label: '8+ years', value: '120' },
]

/** Sidebar filters for the catalog page. */
export default function CatalogFilters({
  values,
  categories,
  brands,
  onChange,
  onReset,
}: CatalogFiltersProps) {
  return (
    <aside className="card h-fit p-5">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="font-display text-lg text-ink-900">Filters</h2>
        <button type="button" onClick={onReset} className="text-sm text-brand-700 hover:underline">
          Reset
        </button>
      </div>

      <div className="space-y-4">
        <div>
          <label className="label" htmlFor="filter-search">
            Search
          </label>
          <input
            id="filter-search"
            className="input"
            placeholder="Blocks, telescope, plush…"
            value={values.q}
            onChange={(event) => onChange({ q: event.target.value })}
          />
        </div>

        <div>
          <label className="label" htmlFor="filter-category">
            Category
          </label>
          <select
            id="filter-category"
            className="input"
            value={values.category}
            onChange={(event) => onChange({ category: event.target.value })}
          >
            <option value="">All categories</option>
            {categories.map((category) => (
              <option key={category.id} value={category.slug}>
                {category.name} ({category.product_count})
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="label" htmlFor="filter-age">
            Child's age
          </label>
          <select
            id="filter-age"
            className="input"
            value={values.ageMonths}
            onChange={(event) => onChange({ ageMonths: event.target.value })}
          >
            {AGE_BANDS.map((band) => (
              <option key={band.label} value={band.value}>
                {band.label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <span className="label">Price (USD)</span>
          <div className="flex items-center gap-2">
            <input
              className="input"
              type="number"
              min={0}
              placeholder="Min"
              aria-label="Minimum price"
              value={values.minPrice}
              onChange={(event) => onChange({ minPrice: event.target.value })}
            />
            <span className="text-ink-700">–</span>
            <input
              className="input"
              type="number"
              min={0}
              placeholder="Max"
              aria-label="Maximum price"
              value={values.maxPrice}
              onChange={(event) => onChange({ maxPrice: event.target.value })}
            />
          </div>
        </div>

        <div>
          <label className="label" htmlFor="filter-brand">
            Brand
          </label>
          <select
            id="filter-brand"
            className="input"
            value={values.brand}
            onChange={(event) => onChange({ brand: event.target.value })}
          >
            <option value="">All brands</option>
            {brands.map((brand) => (
              <option key={brand} value={brand}>
                {brand}
              </option>
            ))}
          </select>
        </div>

        <label className="flex items-center gap-2 text-sm text-ink-700">
          <input
            type="checkbox"
            className="h-4 w-4 rounded border-ink-800/20 text-brand-600 focus:ring-brand-500"
            checked={values.inStock}
            onChange={(event) => onChange({ inStock: event.target.checked })}
          />
          In stock only
        </label>
      </div>
    </aside>
  )
}
