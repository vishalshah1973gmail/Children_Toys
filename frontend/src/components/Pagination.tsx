interface PaginationProps {
  page: number
  pages: number
  onChange: (page: number) => void
}

/** Previous / next pager with a compact window of page numbers. */
export default function Pagination({ page, pages, onChange }: PaginationProps) {
  if (pages <= 1) return null

  const window: number[] = []
  const start = Math.max(1, Math.min(page - 2, pages - 4))
  const end = Math.min(pages, start + 4)
  for (let index = start; index <= end; index += 1) window.push(index)

  return (
    <nav className="mt-8 flex items-center justify-center gap-2" aria-label="Pagination">
      <button
        type="button"
        className="btn-secondary"
        onClick={() => onChange(page - 1)}
        disabled={page <= 1}
      >
        Previous
      </button>
      {window.map((number) => (
        <button
          key={number}
          type="button"
          aria-current={number === page ? 'page' : undefined}
          onClick={() => onChange(number)}
          className={
            number === page
              ? 'btn bg-ink-900 text-white'
              : 'btn-ghost border border-transparent hover:border-ink-800/10'
          }
        >
          {number}
        </button>
      ))}
      <button
        type="button"
        className="btn-secondary"
        onClick={() => onChange(page + 1)}
        disabled={page >= pages}
      >
        Next
      </button>
    </nav>
  )
}
