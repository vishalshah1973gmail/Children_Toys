import { Link } from 'react-router-dom'

import { assetUrl } from '../../api/client'
import { formatAgeRange, formatMoney } from '../../lib/format'
import type { ChatProduct } from '../../types'

/** A product the assistant mentioned, with live price and stock from the database. */
export default function ProductCard({ product }: { product: ChatProduct }) {
  const image = assetUrl(product.image_url)
  return (
    <article className="flex gap-3 rounded-xl border border-ink-800/10 bg-white p-2.5 shadow-sm">
      {image ? (
        <img src={image} alt="" loading="lazy" className="h-16 w-16 shrink-0 rounded-lg object-cover" />
      ) : (
        <div aria-hidden="true" className="h-16 w-16 shrink-0 rounded-lg bg-orange-100" />
      )}
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-bold text-ink-900">{product.name}</p>
        <p className="truncate text-xs text-ink-700">
          {product.brand} · {formatAgeRange(product.min_age_months, product.max_age_months)}
        </p>
        <div className="mt-1.5 flex items-center justify-between gap-2">
          <p className="text-sm font-extrabold text-brand-700">
            {formatMoney(product.price_cents)}
            <span
              className={`ml-2 text-xs font-semibold ${product.in_stock ? 'text-emerald-700' : 'text-red-700'}`}
            >
              {product.in_stock ? 'In stock' : 'Out of stock'}
            </span>
          </p>
          <Link
            to={`/product/${product.slug}`}
            aria-label={`View ${product.name}`}
            className="shrink-0 rounded-full bg-brand-600 px-3 py-1 text-xs font-bold text-white hover:bg-brand-700"
          >
            View
          </Link>
        </div>
      </div>
    </article>
  )
}
