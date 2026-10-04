// Pure text -> structure helpers for chat replies. No imports and only erasable TypeScript
// syntax, so Node can run this file directly in tests.

export type Inline =
  | { kind: 'text'; text: string }
  | { kind: 'bold'; text: string }
  | { kind: 'code'; text: string }
  | { kind: 'link'; text: string; href: string; internal: boolean }

export type Block =
  | { kind: 'paragraph'; lines: Inline[][] }
  | { kind: 'heading'; content: Inline[] }
  | { kind: 'ordered'; items: Inline[][] }
  | { kind: 'bullets'; items: Inline[][] }

// Product pages in older knowledge-base text use this address.
const LOCAL_DEV_ORIGIN = 'http://localhost:5173'
const SITE_ROUTE =
  'catalog(?:\\?[\\w=&%.-]*)?|cart|login|register|feedback|orders|account|checkout\\/guest|product\\/[a-z0-9-]+'
const SITE_PATH = new RegExp(`^\\/(?:${SITE_ROUTE})$`)
// No lookbehind (unsupported before Safari 16.4, where a bad regex would break the whole site
// at import time), and every quantifier on reply text is bounded so odd input cannot make it slow.
// Groups: 1 bold, 2 code, 3 markdown link label, 4 markdown link target, 5 bare URL,
// 6 character before a bare site path, 7 bare site path.
const INLINE_PATTERN = new RegExp(
  [
    '\\*\\*([^*\\n]{1,300}?)\\*\\*',
    '`([^`\\n]{1,200})`',
    '\\[([^\\]\\n]{1,150})\\]\\(([^)\\s]{1,500})\\)',
    '(https?:\\/\\/[^\\s<>()"\']{1,500})',
    `(^|[\\s("'])(\\/(?:${SITE_ROUTE})(?![\\w/-]))`,
  ].join('|'),
  'g',
)
const TRAILING_PUNCTUATION = /[.,;:!?]+$/
const ORDERED_ITEM = /^\s*\d+[.)]\s+(.*)$/
const BULLET_ITEM = /^\s*[-*+•]\s+(.*)$/
const HEADING = /^\s{0,3}#{1,6}\s+(.+)$/
const RULE = /^\s*([-*_])(?:\s*\1){2,}\s*$/

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

function hostOf(href: string): string {
  try {
    return new URL(href).hostname
  } catch {
    return href
  }
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
    const whole = match[0]
    pushText(line.slice(cursor, index))
    if (match[1] !== undefined) {
      parts.push({ kind: 'bold', text: match[1] })
    } else if (match[2] !== undefined) {
      parts.push({ kind: 'code', text: match[2] })
    } else if (match[3] !== undefined) {
      // [label](target): the label is what the shopper reads, so an outside destination also
      // shows its host and a friendly label cannot hide where the link goes.
      const link = resolveLink(match[4], siteOrigin)
      if (link) {
        const label = link.internal ? match[3] : `${match[3]} (${hostOf(link.href)})`
        parts.push({ kind: 'link', text: label, href: link.href, internal: link.internal })
      } else {
        pushText(whole)
      }
    } else {
      // A bare path carries its preceding character in group 6; the link itself is group 7.
      if (match[7] !== undefined) pushText(match[6])
      const raw = match[7] ?? match[5]
      const linkText = raw.replace(TRAILING_PUNCTUATION, '')
      const link = resolveLink(linkText, siteOrigin)
      if (link) {
        // Same-site addresses read better as the page path than as a full localhost URL.
        parts.push({
          kind: 'link',
          text: link.internal ? link.href : linkText,
          href: link.href,
          internal: link.internal,
        })
        pushText(raw.slice(linkText.length))
      } else {
        pushText(raw)
      }
    }
    cursor = index + whole.length
  }
  pushText(line.slice(cursor))
  return parts
}

/** Drops closing hashes ("## Title ##") without a regex, so long lines stay linear. */
function stripClosingHashes(value: string): string {
  let end = value.length
  while (end > 0 && value[end - 1] === '#') end--
  if (end < value.length && end > 0 && value[end - 1] === ' ') return value.slice(0, end).trimEnd()
  return value
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
    if (!line.trim() || RULE.test(line)) {
      flushParagraph()
      continue
    }
    const heading = HEADING.exec(line)
    if (heading) {
      const title = stripClosingHashes(heading[1].trim())
      if (title) {
        flushParagraph()
        blocks.push({ kind: 'heading', content: parseInline(title, siteOrigin) })
        continue
      }
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
