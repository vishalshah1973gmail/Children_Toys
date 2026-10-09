import { type ReactNode, useEffect, useId, useRef } from 'react'

interface DialogProps {
  title: string
  onClose: () => void
  children: ReactNode
  actions: ReactNode
}

/** Centered modal. Escape and a click on the backdrop both call onClose. */
export default function Dialog({ title, onClose, children, actions }: DialogProps) {
  const panelRef = useRef<HTMLDivElement>(null)
  const titleId = useId()
  // Callers pass inline arrows; a ref keeps the effect mount-only so re-renders never re-steal focus.
  const onCloseRef = useRef(onClose)
  onCloseRef.current = onClose

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === 'Escape') onCloseRef.current()
    }
    document.addEventListener('keydown', onKey)
    // A child may already hold focus via autoFocus; don't take it back.
    if (!panelRef.current?.contains(document.activeElement)) panelRef.current?.focus()
    return () => document.removeEventListener('keydown', onKey)
  }, [])

  return (
    <div
      className="fixed inset-0 z-[60] grid place-items-center bg-ink-900/50 p-4"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose()
      }}
    >
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        tabIndex={-1}
        className="card w-full max-w-md p-6 focus:outline-none"
      >
        <h2 id={titleId} className="font-display text-xl text-ink-900">
          {title}
        </h2>
        <div className="mt-3 text-base text-ink-700">{children}</div>
        <div className="mt-6 flex justify-end gap-2">{actions}</div>
      </div>
    </div>
  )
}
