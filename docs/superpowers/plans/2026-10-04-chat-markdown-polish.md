# Chat Markdown Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the chat widget render the common markdown an LLM produces (`[text](url)` links, `*`/`+` bullets, `#` headings, `` `code` ``, `---` rules) instead of showing it raw, show in-app links as readable paths, and stop "Out of stock" from wrapping on narrow product cards.

**Architecture:** Extend the dependency-free `chatText.ts` parser (still no imports, no lookbehind, bounded regex quantifiers) and its renderer `ChatMessageBody.tsx`; one class change in `ProductCard.tsx`; docs.

**Tech Stack:** TypeScript, React 18, Tailwind; Node 24 built-in `node --test` (plain `node --test` from `frontend/`).

**Spec:** `docs/superpowers/specs/2026-10-04-chat-ui-enhancements-design.md` (section "Reply formatting"); this plan widens that section's grammar at the user's request ("apply all the Nice to have").

## Global Constraints

- `frontend/src/components/chat/chatText.ts` keeps **no imports**, only erasable TypeScript, **no regex lookbehind** (Safari < 16.4 would throw at import and break the whole site), and every quantifier on user-controlled text must be **bounded or provably linear** (no nested unbounded quantifiers; no `\s+`/`\s*` followed by something that can fail after a long space run).
- Reply text is never inserted as HTML. Links only for `http(s)` URLs and the site's own routes, validated by `resolveLink`; a markdown link whose target does not validate stays as raw text. External links keep `target="_blank" rel="noopener noreferrer"`.
- No new packages; `package.json`, `tsconfig.json`, lockfiles untouched. Tests run with plain `node --test` from `frontend/` (NOT `node --test tests/`).
- 2-space indent, no semicolons, comments only for non-obvious WHY. Commit by explicit path (never `git add -A`/`.`), trailer `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`, local only, no push.

## Review Focus

1. Markdown links must never create an unsafe link: `[x](javascript:alert(1))`, `[x](data:text/html,x)`, `[x](//evil.com)`, `[x](file:///etc/passwd)` stay raw text; external ones show the host next to the label so a friendly label cannot hide the destination. Pinned by tests in Task 1.
2. Adversarial long inputs (50,000 repetitions of `[`, `` ` ``, `**`, `#`, `- `, spaces, `(`) must parse in well under a second. Pinned by a timing test in Task 1.
3. A bold-led line (`**Note:** ...`) must still be a paragraph, not a bullet or rule. Pinned in Task 1.

---

### Task 1: Markdown grammar, card label, docs

**Files:**
- Modify: `frontend/src/components/chat/chatText.ts`, `frontend/src/components/chat/ChatMessageBody.tsx`, `frontend/src/components/chat/ProductCard.tsx`, `frontend/tests/chatText.test.mjs`, `CLAUDE.md`, `README.md`

**Interfaces:**
- Consumes: existing exports `parseInline(line, siteOrigin): Inline[]`, `parseReply(text, siteOrigin): Block[]`.
- Produces: same function signatures; `Inline` gains `{ kind: 'code'; text: string }`; `Block` gains `{ kind: 'heading'; content: Inline[] }`. `ChatMessageBody` renders both new kinds.

- [ ] **Step 1: Update and add tests first** (RED). In `frontend/tests/chatText.test.mjs`:

(a) Two existing tests change their expected link *text* (internal URLs now display as a readable path): in `'a localhost product URL becomes an in-app link and trailing punctuation stays text'` the link object's `text` becomes `'/product/castle-quest-brick-set'`; in `'a same-origin URL on another origin value is also in-app'` the link's `text` becomes `'/catalog?category=stem'`. Nothing else about those tests changes.

(b) Add these tests (all must fail before Step 3 and pass after):

```js
test('a markdown link to a site page shows its label and links in-app', () => {
  assert.deepEqual(parseInline('Open [your cart](/cart) now', ORIGIN), [
    text('Open '),
    { kind: 'link', text: 'your cart', href: '/cart', internal: true },
    text(' now'),
  ])
})

test('a markdown link to another site shows the host next to the label', () => {
  const parts = parseInline('See [the guide](https://example.com/docs/a) please', ORIGIN)
  assert.deepEqual(parts[1], {
    kind: 'link',
    text: 'the guide (example.com)',
    href: 'https://example.com/docs/a',
    internal: false,
  })
})

test('markdown links with unsafe targets stay raw text', () => {
  for (const input of [
    '[x](javascript:alert(1))',
    '[x](data:text/html,hi)',
    '[x](//evil.com/a)',
    '[x](file:///etc/passwd)',
    '[x](vbscript:run)',
  ]) {
    const parts = parseInline(input, ORIGIN)
    assert.ok(parts.every((part) => part.kind !== 'link'), input)
    assert.equal(parts.map((part) => part.text).join(''), input)
  }
})

test('an unclosed markdown link stays text', () => {
  assert.deepEqual(parseInline('[label](https://example.com', ORIGIN)[0].kind, 'text')
})

test('inline code becomes a code part', () => {
  assert.deepEqual(parseInline('Run `npm test` first', ORIGIN), [
    text('Run '),
    { kind: 'code', text: 'npm test' },
    text(' first'),
  ])
})

test('star and plus bullets become a bullet list', () => {
  const blocks = parseReply('* one\n+ two\n- three', ORIGIN)
  assert.equal(blocks.length, 1)
  assert.equal(blocks[0].kind, 'bullets')
  assert.equal(blocks[0].items.length, 3)
})

test('a line that starts with bold is a paragraph, not a bullet or rule', () => {
  const blocks = parseReply('**Note:** prices change\n**Also** this', ORIGIN)
  assert.equal(blocks.length, 1)
  assert.equal(blocks[0].kind, 'paragraph')
})

test('hash headings become heading blocks and trailing hashes are dropped', () => {
  const blocks = parseReply('## Shipping ##\ntext', ORIGIN)
  assert.equal(blocks[0].kind, 'heading')
  assert.deepEqual(blocks[0].content, [text('Shipping')])
  assert.equal(blocks[1].kind, 'paragraph')
})

test('a hash without a space is not a heading', () => {
  const blocks = parseReply('#hashtag here', ORIGIN)
  assert.equal(blocks[0].kind, 'paragraph')
})

test('horizontal rules are dropped and split paragraphs', () => {
  const blocks = parseReply('before\n---\nafter\n* * *\nend', ORIGIN)
  assert.deepEqual(blocks.map((block) => block.kind), ['paragraph', 'paragraph', 'paragraph'])
})

test('adversarial long inputs parse quickly', () => {
  const cases = [
    '['.repeat(50000),
    '`'.repeat(50000),
    '**'.repeat(25000),
    '(' .repeat(50000),
    '# ' + ' '.repeat(50000) + 'x',
    '- ' + ' '.repeat(50000) + 'x',
    '-' + ' '.repeat(50000) + 'x',
    '- '.repeat(25000),
    '1. ' + '[a](b'.repeat(10000),
    'http://'.repeat(10000),
  ]
  for (const input of cases) {
    const started = performance.now()
    parseReply(input, ORIGIN)
    const elapsed = performance.now() - started
    assert.ok(elapsed < 500, `${elapsed.toFixed(0)}ms for ${input.slice(0, 12)}`)
  }
})
```

Run `node --test tests/chatText.test.mjs` from `frontend/` to see RED (the new tests and the two changed ones fail).

- [ ] **Step 2: Replace `frontend/src/components/chat/chatText.ts`** with:

```ts
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
```

Run `node --test tests/chatText.test.mjs` from `frontend/`. Expected: all pass (GREEN), including the timing test. If the timing test or any other fails, fix the **implementation** (never loosen the test) and report what you changed. Watch for: `RULE` is checked before the bullet pattern so `* * *` is a rule, while `**Bold**` never matches RULE or BULLET_ITEM (second character is not whitespace).

- [ ] **Step 3: Renderer.** In `frontend/src/components/chat/ChatMessageBody.tsx`:
  - In `InlineParts`, add (before the `link` branch):
    ```tsx
    if (part.kind === 'code') {
      return (
        <code key={index} className="rounded bg-orange-100 px-1 py-0.5 text-[13px] text-ink-900">
          {part.text}
        </code>
      )
    }
    ```
  - In `ChatMessageBody`'s block map, add (before the `ordered` branch):
    ```tsx
    if (block.kind === 'heading') {
      return (
        <p key={index} className="font-extrabold text-ink-900">
          <InlineParts parts={block.content} />
        </p>
      )
    }
    ```
  No other changes.

- [ ] **Step 4: Product card label.** In `frontend/src/components/chat/ProductCard.tsx` add `whitespace-nowrap` to the class list of the "In stock / Out of stock" `<span>` so the label never splits across two lines. No other change.

- [ ] **Step 5: Docs.** In `CLAUDE.md` (Chatbot subsection) and `README.md` (section 13), update the sentence that lists what the reply formatter supports so it is accurate: paragraphs, numbered lists, bullet lists (`-`, `*`, `+`, `•`), `#` headings (shown as bold lines), `**bold**`, `` `inline code` ``, `---` rules (dropped), `[label](target)` links and bare URLs or site paths; links only for `http(s)` URLs and the site's own routes (an outside link shows its host next to the label; same-site addresses show as the page path), anything else stays plain text and nothing is inserted as HTML. Also, in README section 13 add one short note: Lyzr's upload accepts only PDF, DOCX and TXT, so `docs/chatbot-kb/upload/` holds `.txt` copies of `docs/chatbot-kb/*.md` for uploading; after editing a `.md` doc, copy it over its `.txt` twin (PowerShell: `Copy-Item docs\chatbot-kb\05-shipping-tax-pricing.md docs\chatbot-kb\upload\05-shipping-tax-pricing.txt`), and `products.txt` is `products.md` copied the same way. Keep each doc's tone; no placeholders; make sure no text line sits directly above a `---` rule.

- [ ] **Step 6: Verify** from `frontend/`: `npm run typecheck`, `npm run build` (both exit 0), `node --test` (all pass: report the count); from `backend/`: `python -m pytest -q` (all pass).

- [ ] **Step 7: Commit** (three commits, explicit paths):
  1. `git add frontend/src/components/chat/chatText.ts frontend/src/components/chat/ChatMessageBody.tsx frontend/tests/chatText.test.mjs` → `feat: render markdown links, bullets, headings and code in chat replies`
  2. `git add frontend/src/components/chat/ProductCard.tsx` → `fix: keep the stock label on one line in product cards`
  3. `git add CLAUDE.md README.md` → `docs: document the wider reply formatting and the Lyzr upload copies`

---

## Self-Review

- **Spec coverage:** the "Nice to have" list items 1 (raw markdown), 2 (card label wrap) and the "localhost link text" minor are implemented; items 3 (delete test customer, scratch files) and the upload-folder commit were done before this plan.
- **Placeholders:** none.
- **Type consistency:** `Inline`/`Block` unions match their uses in `ChatMessageBody`; `parseInline`/`parseReply` signatures unchanged.
- **Risk:** the regex surface grew; bounded quantifiers and the adversarial timing test are the control.
