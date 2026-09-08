import { Link } from 'react-router-dom'

import { assetUrl } from '../api/client'
import { formatAgeRange, formatMoney } from '../lib/format'
import type { Product } from '../types'

interface ProductCardProps {
  product: Product
  onAdd?: (product: Product) => void
}

/** Catalog tile: image, price, age range and a quick add-to-cart. */
export default function ProductCard({ product, onAdd }: ProductCardProps) {
  const soldOut = product.stock_quantity <= 0

  return (
    <article className="card group flex flex-col overflow-hidden transition hover:shadow-md">
      <Link to={`/product/${product.slug}`} className="block overflow-hidden bg-orange-50">
        <img
          src={assetUrl(product.primary_image_url)}
          alt={product.name}
          loading="lazy"
          className="h-52 w-full object-cover transition duration-300 group-hover:scale-[1.03]"
        />
      </Link>

      <div className="flex flex-1 flex-col gap-2 p-4">
        <div className="flex items-center justify-between text-xs text-ink-700">
          <span className="badge bg-orange-100 text-brand-800">{product.category.name}</span>
          <span>{formatAgeRange(product.min_age_months, product.max_age_months)}</span>
        </div>

        <h3 className="font-display text-lg leading-snug text-ink-900">
          <Link to={`/product/${product.slug}`} className="hover:text-brand-700">
            {product.name}
          </Link>
        </h3>

        <p className="line-clamp-2 text-sm text-ink-700">{product.description}</p>

        <div className="mt-auto flex items-center justify-between pt-3">
          <div>
            <p className="text-lg font-semibold text-ink-900">{formatMoney(product.price_cents)}</p>
            <p className={`text-xs ${soldOut ? 'text-red-600' : 'text-emerald-700'}`}>
              {soldOut ? 'Sold out' : `${product.stock_quantity} in stock`}
            </p>
          </div>
          {onAdd && (
            <button
              type="button"
              className="btn-primary"
              disabled={soldOut}
              onClick={() => onAdd(product)}
            >
              Add to cart
            </button>
          )}
        </div>
      </div>
    </article>
  )
}
