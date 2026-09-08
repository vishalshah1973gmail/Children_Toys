interface SpinnerProps {
  label?: string
}

/** Centred loading indicator used while a page fetches. */
export default function Spinner({ label = 'Loading…' }: SpinnerProps) {
  return (
    <div className="flex items-center justify-center gap-3 py-16 text-ink-700">
      <span
        className="h-5 w-5 animate-spin rounded-full border-2 border-brand-500 border-t-transparent"
        aria-hidden="true"
      />
      <span className="text-sm">{label}</span>
    </div>
  )
}
