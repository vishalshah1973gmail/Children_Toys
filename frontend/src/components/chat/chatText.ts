// Pure text -> structure helpers for chat replies. No imports and only erasable TypeScript
// syntax, so Node can run this file directly in tests.

export type Inline =
  | { kind: 'text'; text: string }
  | { kind: 'bold'; text: string }
  | { kind: 'link'; text: string; href: string; internal: boolean }

export type Block =
  | { kind: 'paragraph'; lines: Inline[][] }
  | { kind: 'ordered'; items: Inline[][] }
  | { kind: 'bullets'; items: Inline[][] }

// Product pages in older knowledge-base text use this address.
const LOCAL_DEV_ORIGIN = 'http://localhost:5173'
const SITE_ROUTE =
  'catalog(?:\\?[\\w=&%.-]*)?|cart|login|register|feedback|orders|account|checkout\\/guest|product\\/[a-z0-9-]+'
const SITE_PATH = new RegExp(`^\\/(?:${SITE_ROUTE})$`)
// No lookbehind (unsupported before Safari 16.4, where a bad regex would break the whole site
// at import time): a bare path must follow the start of the line, whitespace, a bracket or a quote.
// Groups: 1 bold text, 2 full URL, 3 character before a bare path, 4 bare path.
const INLINE_PATTERN = new RegExp(
  [
    '\\*\\*([^*\\n]+?)\\*\\*',
    '(https?:\\/\\/[^\\s<>()"\']+)',
    `(^|[\\s("'])(\\/(?:${SITE_ROUTE})(?![\\w/-]))`,
  ].join('|'),
  'g',
)
const TRAILING_PUNCTUATION = /[.,;:!?]+$/
const ORDERED_ITEM = /^\s*\d+[.)]\s+(.*)$/
const BULLET_ITEM = /^\s*[-•]\s+(.*)$/

function resolveLink(target: string, siteOrigin: string): { href: string; internal: boolean } | null {
  if (target.startsWith('/')) return SITE_PATH.test(target) ? { href: target, internal: true } : null
  let url: URL
  try {
    url = new URL(target)
  } catch {
    return null
  }
  if (url.protocol !== 'http:' && url.protocol !== 'https:') return null
  const path = url.pathname + url.search
  const sameSite = url.origin === siteOrigin || url.origin === LOCAL_DEV_ORIGIN
  if (sameSite && SITE_PATH.test(path)) return { href: path, internal: true }
  return { href: url.href, internal: false }
}

export function parseInline(line: string, siteOrigin: string): Inline[] {
  const parts: Inline[] = []
  let cursor = 0
  const pushText = (value: string) => {
    if (!value) return
    const last = parts[parts.length - 1]
    if (last && last.kind === 'text') last.text += value
    else parts.push({ kind: 'text', text: value })
  }
  for (const match of line.matchAll(INLINE_PATTERN)) {
    const index = match.index ?? 0
    pushText(line.slice(cursor, index))
    if (match[1] !== undefined) {
      parts.push({ kind: 'bold', text: match[1] })
    } else {
      // A bare path carries its preceding character in group 3; the link itself is group 4.
      if (match[4] !== undefined) pushText(match[3])
      const raw = match[4] ?? match[0]
      const linkText = raw.replace(TRAILING_PUNCTUATION, '')
      const link = resolveLink(linkText, siteOrigin)
      if (link) {
        parts.push({ kind: 'link', text: linkText, href: link.href, internal: link.internal })
        pushText(raw.slice(linkText.length))
      } else {
        pushText(raw)
      }
    }
    cursor = index + match[0].length
  }
  pushText(line.slice(cursor))
  return parts
}

export function parseReply(text: string, siteOrigin: string): Block[] {
  const blocks: Block[] = []
  let paragraph: Inline[][] = []
  const flushParagraph = () => {
    if (paragraph.length > 0) {
      blocks.push({ kind: 'paragraph', lines: paragraph })
      paragraph = []
    }
  }

  for (const rawLine of text.replace(/\r\n/g, '\n').split('\n')) {
    const line = rawLine.trimEnd()
    if (!line.trim()) {
      flushParagraph()
      continue
    }
    const ordered = ORDERED_ITEM.exec(line)
    if (ordered) {
      flushParagraph()
      const item = parseInline(ordered[1], siteOrigin)
      const last = blocks[blocks.length - 1]
      if (last && last.kind === 'ordered') last.items.push(item)
      else blocks.push({ kind: 'ordered', items: [item] })
      continue
    }
    const bullet = BULLET_ITEM.exec(line)
    if (bullet) {
      flushParagraph()
      const item = parseInline(bullet[1], siteOrigin)
      const last = blocks[blocks.length - 1]
      if (last && last.kind === 'bullets') last.items.push(item)
      else blocks.push({ kind: 'bullets', items: [item] })
      continue
    }
    paragraph.push(parseInline(line.trim(), siteOrigin))
  }
  flushParagraph()
  return blocks
}
