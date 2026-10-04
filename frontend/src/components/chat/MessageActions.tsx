import { useEffect, useState } from 'react'

const FEEDBACK_KEY = 'toybox.chat_feedback'
type Vote = 'up' | 'down'

function readVotes(): Record<string, Vote> {
  try {
    const raw = localStorage.getItem(FEEDBACK_KEY)
    return raw ? (JSON.parse(raw) as Record<string, Vote>) : {}
  } catch {
    return {}
  }
}

function writeVote(id: string, vote: Vote | null) {
  try {
    const votes = readVotes()
    if (vote) votes[id] = vote
    else delete votes[id]
    localStorage.setItem(FEEDBACK_KEY, JSON.stringify(votes))
  } catch {
    // Storage blocked: the choice is simply not remembered.
  }
}

const ICON = {
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 2,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
  'aria-hidden': true,
  className: 'h-4 w-4',
}

const BUTTON =
  'grid h-7 w-7 place-items-center rounded-full text-ink-700 hover:bg-orange-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500'

/** Copy and thumbs up/down for one bot reply. Votes live in this browser only. */
export default function MessageActions({ id, text }: { id: string; text: string }) {
  const [copied, setCopied] = useState(false)
  const [vote, setVote] = useState<Vote | null>(() => readVotes()[id] ?? null)

  useEffect(() => {
    if (!copied) return
    const timer = window.setTimeout(() => setCopied(false), 1500)
    return () => window.clearTimeout(timer)
  }, [copied])

  async function copy() {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
    } catch {
      // Clipboard unavailable: nothing to show.
    }
  }

  function choose(next: Vote) {
    const value = vote === next ? null : next
    setVote(value)
    writeVote(id, value)
  }

  return (
    <div className="flex items-center gap-1">
      <button type="button" onClick={copy} className={BUTTON} aria-label="Copy answer" title="Copy answer">
        {copied ? (
          <svg {...ICON}>
            <polyline points="20 6 9 17 4 12" />
          </svg>
        ) : (
          <svg {...ICON}>
            <rect x="9" y="9" width="11" height="11" rx="2" />
            <path d="M5 15V6a2 2 0 0 1 2-2h9" />
          </svg>
        )}
      </button>
      {copied && (
        <span role="status" className="text-xs font-semibold text-emerald-700">
          Copied
        </span>
      )}
      <button
        type="button"
        onClick={() => choose('up')}
        aria-pressed={vote === 'up'}
        className={`${BUTTON} ${vote === 'up' ? 'bg-orange-100 text-brand-700' : ''}`}
        aria-label="Helpful"
        title="Helpful"
      >
        <svg {...ICON}>
          <path d="M7 10v10H3V10zM7 10l4-7a2 2 0 0 1 2 2v4h6a2 2 0 0 1 2 2l-1.5 7a2 2 0 0 1-2 1.5H7" />
        </svg>
      </button>
      <button
        type="button"
        onClick={() => choose('down')}
        aria-pressed={vote === 'down'}
        className={`${BUTTON} ${vote === 'down' ? 'bg-orange-100 text-brand-700' : ''}`}
        aria-label="Not helpful"
        title="Not helpful"
      >
        <svg {...ICON}>
          <path d="M17 14V4h4v10zM17 14l-4 7a2 2 0 0 1-2-2v-4H5a2 2 0 0 1-2-2l1.5-7A2 2 0 0 1 6.5 4H17" />
        </svg>
      </button>
    </div>
  )
}
