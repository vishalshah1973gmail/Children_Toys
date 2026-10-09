import { FormEvent, useEffect, useRef, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'

import { sendChatMessage } from '../api/chat'
import { toApiError } from '../api/client'
import { useAuthStore } from '../store/authStore'
import type { ChatProduct } from '../types'
import Dialog from './Dialog'
import { CHAT_LOGIN_REQUIRED_MESSAGE } from './chat/chatGate'
import ChatMessageBody from './chat/ChatMessageBody'
import MessageActions from './chat/MessageActions'
import ProductCard from './chat/ProductCard'
import SuggestionChips from './chat/SuggestionChips'
import { STARTER_QUESTIONS, followUpQuestions } from './chat/chatSuggestions'

type ChatMessage = {
  id: string
  role: 'user' | 'bot'
  text: string
  time: number
  products?: ChatProduct[]
  suggestions?: string[]
}

const SESSION_KEY = 'toybox.chat_session'
const MAX_CHARS = 500
const GREETING = "Hi! I'm the ToyBox assistant. Ask me about products, checkout, shipping or tax."

function greeting(): ChatMessage {
  return { id: 'greeting', role: 'bot', text: GREETING, time: Date.now() }
}

// Both forms match the backend pattern ^[A-Za-z0-9_-]{8,64}$.
function newSessionId(): string {
  return crypto.randomUUID?.() ?? `s${Date.now()}${Math.random().toString(36).slice(2)}`
}

function startNewSession(): string {
  const created = newSessionId()
  try {
    localStorage.setItem(SESSION_KEY, created)
  } catch {
    // Storage blocked: the id lives in memory for this page only.
  }
  return created
}

/** Falls back to an in-memory id when localStorage is blocked. */
function loadSessionId(): string {
  try {
    const existing = localStorage.getItem(SESSION_KEY)
    if (existing) return existing
  } catch {
    return newSessionId()
  }
  return startNewSession()
}

const FONT_LINK_ID = 'toybox-chat-font'
const FONT_URL = 'https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800&display=swap'

// The font is chat-only, so it is fetched on first open instead of on every page load.
function ensureChatFont() {
  if (document.getElementById(FONT_LINK_ID)) return
  const link = document.createElement('link')
  link.id = FONT_LINK_ID
  link.rel = 'stylesheet'
  link.href = FONT_URL
  document.head.appendChild(link)
}

function formatTime(time: number): string {
  return new Date(time).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })
}

function Avatar({ size }: { size: 'sm' | 'md' }) {
  const box = size === 'md' ? 'h-10 w-10' : 'h-7 w-7'
  const icon = size === 'md' ? 'h-6 w-6' : 'h-4 w-4'
  return (
    <span
      aria-hidden="true"
      className={`grid shrink-0 place-items-center rounded-full bg-white text-brand-600 shadow-sm ${box}`}
    >
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
        className={icon}
      >
        <rect x="4" y="7" width="16" height="12" rx="3" />
        <path d="M12 7V4" />
        <circle cx="12" cy="3.5" r="1" />
        <circle cx="9" cy="13" r="1" fill="currentColor" />
        <circle cx="15" cy="13" r="1" fill="currentColor" />
        <path d="M9.5 16.5c1.5 1 3.5 1 5 0" />
      </svg>
    </span>
  )
}

export default function ChatWidget() {
  const location = useLocation()
  const user = useAuthStore((state) => state.user)
  const [gateOpen, setGateOpen] = useState(false)
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<ChatMessage[]>(() => [greeting()])
  const [draft, setDraft] = useState('')
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const sessionId = useRef<string | null>(null)
  const inFlight = useRef(false)
  const chatGeneration = useRef(0)
  const idCounter = useRef(0)
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const launcherRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    const reduceMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false
    bottomRef.current?.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'end' })
  }, [messages, pending, open])

  useEffect(() => {
    if (!open) return
    ensureChatFont()
    inputRef.current?.focus()
  }, [open])

  // A different person (or none) is now signed in: close the panel and wipe the conversation.
  const userId = user?.id ?? null
  useEffect(() => {
    chatGeneration.current += 1
    inFlight.current = false
    sessionId.current = null
    setOpen(false)
    setMessages([greeting()])
    setDraft('')
    setError(null)
    setPending(false)
    try {
      localStorage.removeItem(SESSION_KEY)
    } catch {
      // Storage blocked: nothing persisted to clear.
    }
  }, [userId])

  // Hooks above must all run before this early return.
  if (location.pathname.startsWith('/admin')) return null

  // The time part keeps ids unique across page loads, so a stored vote can never attach to a new message.
  const makeId = () => `${Date.now().toString(36)}-${idCounter.current++}`

  async function sendText(raw: string) {
    const text = raw.trim()
    if (!text || inFlight.current) return
    // Chips and the Send button unmount or disable below; keep keyboard focus in the panel.
    inputRef.current?.focus()
    // Generated once, lazily, so it is not recomputed on every render.
    if (sessionId.current === null) sessionId.current = loadSessionId()
    const generation = chatGeneration.current
    const asked = [...messages.filter((message) => message.role === 'user').map((m) => m.text), text]
    inFlight.current = true
    setDraft('')
    setError(null)
    setMessages((current) => [...current, { id: makeId(), role: 'user', text, time: Date.now() }])
    setPending(true)
    try {
      const { reply, products } = await sendChatMessage(text, sessionId.current)
      // "New chat" was pressed while waiting: this reply belongs to the old conversation.
      if (generation !== chatGeneration.current) return
      setMessages((current) => [
        ...current,
        {
          id: makeId(),
          role: 'bot',
          text: reply,
          time: Date.now(),
          products,
          suggestions: followUpQuestions(text, reply, asked),
        },
      ])
    } catch (caught) {
      if (generation === chatGeneration.current) setError(toApiError(caught).message)
    } finally {
      if (generation === chatGeneration.current) {
        inFlight.current = false
        setPending(false)
      }
    }
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    void sendText(draft)
  }

  function newChat() {
    chatGeneration.current += 1
    inFlight.current = false
    sessionId.current = startNewSession()
    setMessages([greeting()])
    setDraft('')
    setError(null)
    setPending(false)
    inputRef.current?.focus()
  }

  function openChat() {
    if (!user) {
      setGateOpen(true)
      return
    }
    setOpen(true)
  }

  const hasUserMessage = messages.some((message) => message.role === 'user')
  const lastMessage = messages[messages.length - 1]

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col items-end gap-3 font-chat sm:bottom-6 sm:right-6">
      {open && (
        <section
          aria-label="ToyBox assistant"
          onKeyDown={(event) => {
            if (event.key === 'Escape') {
              setOpen(false)
              launcherRef.current?.focus()
            }
          }}
          className="chat-open flex h-[min(36rem,calc(100dvh-6rem))] max-h-[calc(100vh-6rem)] w-[22rem] max-w-[calc(100vw-2rem)] flex-col overflow-hidden rounded-2xl border border-ink-800/10 bg-[#fffaf5] shadow-2xl"
        >
          <header className="flex items-center gap-3 bg-gradient-to-r from-brand-600 to-brand-700 px-4 py-3 text-white">
            <Avatar size="md" />
            <div className="min-w-0 flex-1">
              <p className="text-base font-extrabold leading-tight">ToyBox assistant</p>
              <p className="flex items-center gap-1.5 text-xs text-white/90">
                <span aria-hidden="true" className="h-2 w-2 rounded-full bg-emerald-300" />
                Here to help
              </p>
            </div>
            <button
              type="button"
              onClick={newChat}
              aria-label="Start a new chat"
              title="Start a new chat"
              className="grid h-9 w-9 place-items-center rounded-full hover:bg-white/15 focus-visible:outline focus-visible:outline-2 focus-visible:outline-white"
            >
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth={2}
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
                className="h-5 w-5"
              >
                <path d="M3 12a9 9 0 0 1 15.5-6.2L21 8" />
                <path d="M21 3v5h-5" />
                <path d="M21 12a9 9 0 0 1-15.5 6.2L3 16" />
                <path d="M3 21v-5h5" />
              </svg>
            </button>
          </header>

          <div className="flex-1 space-y-4 overflow-y-auto px-3 py-4 text-[15px] leading-relaxed" aria-live="polite">
            {messages.map((message, index) => {
              const isLast = message === lastMessage
              if (message.role === 'user') {
                return (
                  <div key={message.id} className="flex flex-col items-end">
                    <p className="max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-br-md bg-brand-600 px-3.5 py-2.5 text-white [overflow-wrap:anywhere]">
                      {message.text}
                    </p>
                    <span className="mt-1 text-[11px] text-ink-700">{formatTime(message.time)}</span>
                  </div>
                )
              }
              const showAvatar = messages[index + 1]?.role !== 'bot'
              return (
                <div key={message.id} className="space-y-2">
                  <div className="flex items-end gap-2">
                    {showAvatar ? <Avatar size="sm" /> : <span className="w-7 shrink-0" />}
                    <div className="min-w-0 max-w-[85%] flex-1">
                      <div className="rounded-2xl rounded-bl-md border border-ink-800/10 bg-white px-3.5 py-2.5 text-ink-800 shadow-sm">
                        <ChatMessageBody text={message.text} />
                      </div>
                    </div>
                  </div>
                  <div className="min-w-0 space-y-2 pl-9">
                    {message.products && message.products.length > 0 && (
                      <div className="space-y-2">
                        {message.products.map((product) => (
                          <ProductCard key={product.slug} product={product} />
                        ))}
                      </div>
                    )}
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] text-ink-700">{formatTime(message.time)}</span>
                      {message.id !== 'greeting' && <MessageActions id={message.id} text={message.text} />}
                    </div>
                    {isLast && !pending && !hasUserMessage && (
                      <SuggestionChips questions={STARTER_QUESTIONS} onPick={(q) => void sendText(q)} />
                    )}
                    {isLast && !pending && message.suggestions && (
                      <SuggestionChips questions={message.suggestions} onPick={(q) => void sendText(q)} />
                    )}
                  </div>
                </div>
              )
            })}

            {pending && (
              <div className="flex items-end gap-2">
                <Avatar size="sm" />
                <div
                  role="status"
                  aria-label="The assistant is typing"
                  className="flex items-center gap-1.5 rounded-2xl rounded-bl-md border border-ink-800/10 bg-white px-4 py-3 shadow-sm"
                >
                  <span className="chat-dot inline-block h-2 w-2 rounded-full bg-ink-700/60" />
                  <span className="chat-dot inline-block h-2 w-2 rounded-full bg-ink-700/60" />
                  <span className="chat-dot inline-block h-2 w-2 rounded-full bg-ink-700/60" />
                </div>
              </div>
            )}
            {error && (
              <p role="alert" className="rounded-xl bg-red-50 px-3 py-2 text-sm text-red-700">
                {error}
              </p>
            )}
            <div ref={bottomRef} />
          </div>

          <form onSubmit={handleSubmit} className="flex items-center gap-2 border-t border-ink-800/10 bg-white p-3">
            <input
              ref={inputRef}
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              maxLength={MAX_CHARS}
              placeholder="Ask a question…"
              aria-label="Your question"
              className="min-w-0 flex-1 rounded-full border border-ink-800/15 bg-orange-50/50 px-4 py-2.5 text-[15px] outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/30"
            />
            <button
              type="submit"
              disabled={pending || !draft.trim()}
              aria-label="Send message"
              className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-brand-600 text-white hover:bg-brand-700 disabled:opacity-40"
            >
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth={2}
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
                className="h-5 w-5"
              >
                <line x1="5" y1="12" x2="19" y2="12" />
                <polyline points="12 5 19 12 12 19" />
              </svg>
            </button>
          </form>
        </section>
      )}
      <div className="flex items-center gap-3">
      {!open && (
        <button
          type="button"
          tabIndex={-1}
          aria-hidden="true"
          onClick={openChat}
          className="rounded-full bg-white px-4 py-2 text-sm font-bold text-ink-900 shadow-lg ring-1 ring-ink-800/10 hover:bg-orange-50"
        >
          Chat with us
        </button>
      )}
      <button
        ref={launcherRef}
        type="button"
        onClick={() => (open ? setOpen(false) : openChat())}
        aria-expanded={open}
        aria-label={open ? 'Close chat' : 'Open chat'}
        title={open ? 'Close chat' : 'Chat with us'}
        className="relative h-16 w-16 rounded-full bg-brand-600 hover:bg-brand-700 text-white shadow-lg grid place-items-center focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2 focus:outline-none sm:h-[72px] sm:w-[72px]"
      >
        {!open && (
          <span
            aria-hidden="true"
            className="pointer-events-none absolute inset-0 rounded-full ring-4 ring-brand-500/50 motion-safe:animate-ping"
          />
        )}
        {open ? (
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
            className="h-6 w-6"
          >
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        ) : (
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
            className="h-6 w-6"
          >
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
        )}
      </button>
      </div>
      {gateOpen && (
        <Dialog
          title="Please log in to chat"
          onClose={() => setGateOpen(false)}
          actions={
            <>
              <Link
                to="/register"
                onClick={() => setGateOpen(false)}
                className="rounded-lg px-3 py-2 text-sm font-medium text-ink-700 hover:bg-orange-100"
              >
                Register
              </Link>
              <Link
                to="/login"
                onClick={() => setGateOpen(false)}
                className="btn-primary px-4 py-2 text-sm"
              >
                Log in
              </Link>
            </>
          }
        >
          {CHAT_LOGIN_REQUIRED_MESSAGE}
        </Dialog>
      )}
    </div>
  )
}
