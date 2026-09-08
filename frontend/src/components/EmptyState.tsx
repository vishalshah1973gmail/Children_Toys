import type { ReactNode } from 'react'

interface EmptyStateProps {
  title: string
  description?: string
  action?: ReactNode
}

/** Shown when a list has no rows. */
export default function EmptyState({ title, description, action }: EmptyStateProps) {
  return (
    <div className="card flex flex-col items-center gap-3 px-6 py-14 text-center">
      <h3 className="font-display text-xl text-ink-900">{title}</h3>
      {description && <p className="max-w-md text-sm text-ink-700">{description}</p>}
      {action}
    </div>
  )
}
