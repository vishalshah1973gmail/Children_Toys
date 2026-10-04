import { useEffect, useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'

import { catalogApi } from '../api/catalog'
import { assetUrl } from '../api/client'
import type { Product } from '../types'

interface SplitPageProps {
  eyebrow: string
  title: string
  subtitle: string
  children: ReactNode
}

/** Full-height two-panel page: toy photos and a big heading beside the form. */
export default function SplitPage({ eyebrow, title, subtitle, children }: SplitPageProps) {
  const [photos, setPhotos] = useState<Product[]>([])

  useEffect(() => {
    let cancelled = false
    catalogApi
      .featured(6)
      .then((products) => {
        if (!cancelled) setPhotos(products)
      })
      .catch(() => {
        // Photos are decoration; the form works without them.
      })
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <section className="card flex w-full flex-1 overflow-hidden">
      <div className="grid w-full lg:grid-cols-2">
        <div className="flex flex-col justify-center bg-gradient-to-br from-orange-50 via-white to-orange-100 p-8 sm:p-12 xl:p-16">
          <p className="badge self-start bg-orange-100 text-base text-brand-800">{eyebrow}</p>
          <h1 className="mt-4 font-display text-4xl leading-tight text-ink-900 sm:text-5xl xl:text-6xl">
            {title}
          </h1>
          <p className="mt-4 max-w-xl text-lg leading-relaxed text-ink-700 xl:text-xl">{subtitle}</p>
          {photos.length > 0 && (
            <div className="mt-10 hidden grid-cols-3 gap-4 lg:grid xl:gap-5">
              {photos.map((product) => (
                <Link
                  key={product.id}
                  to={`/product/${product.slug}`}
                  className="aspect-square overflow-hidden rounded-2xl bg-orange-50 shadow-sm ring-1 ring-ink-800/10 transition hover:-translate-y-0.5 hover:shadow-md"
                >
                  <img
                    src={assetUrl(product.primary_image_url)}
                    alt={product.name}
                    className="h-full w-full object-cover"
                  />
                </Link>
              ))}
            </div>
          )}
        </div>
        <div className="flex items-center justify-center p-8 sm:p-12 xl:p-16">
          <div className="w-full max-w-xl">{children}</div>
        </div>
      </div>
    </section>
  )
}
