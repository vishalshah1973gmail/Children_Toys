interface ErrorBannerProps {
  message: string | null
  onDismiss?: () => void
}

/** Inline, non-blocking error message. */
export default function ErrorBanner({ message, onDismiss }: ErrorBannerProps) {
  if (!message) return null
  return (
    <div
      role="alert"
      className="mb-4 flex items-start justify-between gap-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800"
    >
      <span>{message}</span>
      {onDismiss && (
        <button type="button" onClick={onDismiss} className="font-semibold hover:underline">
          Dismiss
        </button>
      )}
    </div>
  )
}
