import { FormEvent, useEffect, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'

import { sendChatMessage } from '../api/chat'
import { toApiError } from '../api/client'

type ChatMessage = { role: 'user' | 'bot'; text: string }

const SESSION_KEY = 'toybox.chat_session'
const MAX_CHARS = 500
const GREETING = "Hi! I'm the ToyBox assistant. Ask me about products, checkout, shipping or tax."

// Both forms match the backend pattern ^[A-Za-z0-9_-]{8,64}$.
function newSessionId(): string {
  return crypto.randomUUID?.() ?? `s${Date.now()}${Math.random().toString(36).slice(2)}`
}

/** Falls back to an in-memory id when localStorage is blocked. */
function loadSessionId(): string {
  try {
    const existing = localStorage.getItem(SESSION_KEY)
    if (existing) return existing
    const created = newSessionId()
    localStorage.setItem(SESSION_KEY, created)
    return created
  } catch {
    return newSessionId()
  }
}

export default function ChatWidget() {
  const location = useLocation()
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<ChatMessage[]>([{ role: 'bot', text: GREETING }])
  const [draft, setDraft] = useState('')
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const sessionId = useRef<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, pending, open])

  // Hooks above must all run before this early return.
  if (location.pathname.startsWith('/admin')) return null

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    const text = draft.trim()
    if (!text || pending) return
    // Generated once, lazily, so it is not recomputed on every render.
    if (sessionId.current === null) sessionId.current = loadSessionId()
    setDraft('')
    setError(null)
    setMessages((current) => [...current, { role: 'user', text }])
    setPending(true)
    try {
      const reply = await sendChatMessage(text, sessionId.current)
      setMessages((current) => [...current, { role: 'bot', text: reply }])
    } catch (caught) {
      setError(toApiError(caught).message)
    } finally {
      setPending(false)
    }
  }

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col items-end gap-2">
      {open && (
        <section
          aria-label="ToyBox assistant"
          className="card flex h-[28rem] w-80 max-w-[calc(100vw-2rem)] flex-col overflow-hidden shadow-xl"
        >
          <header className="bg-brand-600 px-4 py-3 text-sm font-semibold text-white">
            ToyBox assistant
          </header>
          <div className="flex-1 space-y-2 overflow-y-auto p-3 text-sm" aria-live="polite">
            {messages.map((message, index) => (
              <p
                key={index}
                className={
                  message.role === 'user'
                    ? 'ml-8 whitespace-pre-wrap rounded-lg bg-brand-600 px-3 py-2 text-white'
                    : 'mr-8 whitespace-pre-wrap rounded-lg bg-orange-50 px-3 py-2 text-ink-800'
                }
              >
                {message.text}
              </p>
            ))}
            {pending && <p className="mr-8 rounded-lg bg-orange-50 px-3 py-2 text-ink-700">Typing…</p>}
            {error && (
              <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-red-700">
                {error}
              </p>
            )}
            <div ref={bottomRef} />
          </div>
          <form onSubmit={handleSubmit} className="flex gap-2 border-t border-ink-800/10 p-2">
            <input
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              maxLength={MAX_CHARS}
              placeholder="Ask a question…"
              aria-label="Your question"
              className="input min-w-0 flex-1"
            />
            <button type="submit" disabled={pending || !draft.trim()} className="btn-primary">
              Send
            </button>
          </form>
        </section>
      )}
      <button
        type="button"
        onClick={() => setOpen((current) => !current)}
        aria-expanded={open}
        aria-label={open ? 'Close chat' : 'Open chat'}
        className="btn-primary rounded-full px-4 py-3 shadow-lg"
      >
        {open ? 'Close' : 'Chat'}
      </button>
    </div>
  )
}
