import assert from 'node:assert/strict'
import test from 'node:test'

import { parseInline, parseReply } from '../src/components/chat/chatText.ts'

const ORIGIN = 'http://localhost:5173'
const text = (value) => ({ kind: 'text', text: value })

test('plain text is one text part', () => {
  assert.deepEqual(parseInline('Shipping is $5.99.', ORIGIN), [text('Shipping is $5.99.')])
})

test('bold text becomes a bold part', () => {
  assert.deepEqual(parseInline('This is **important** news', ORIGIN), [
    text('This is '),
    { kind: 'bold', text: 'important' },
    text(' news'),
  ])
})

test('an unmatched ** stays plain text', () => {
  assert.deepEqual(parseInline('oops **not closed', ORIGIN), [text('oops **not closed')])
})

test('a localhost product URL becomes an in-app link and trailing punctuation stays text', () => {
  assert.deepEqual(
    parseInline('See http://localhost:5173/product/castle-quest-brick-set.', ORIGIN),
    [
      text('See '),
      {
        kind: 'link',
        text: '/product/castle-quest-brick-set',
        href: '/product/castle-quest-brick-set',
        internal: true,
      },
      text('.'),
    ],
  )
})

test('a same-origin URL on another origin value is also in-app', () => {
  const parts = parseInline('Go to https://toybox.example/catalog?category=stem now', 'https://toybox.example')
  assert.deepEqual(parts[1], {
    kind: 'link',
    text: '/catalog?category=stem',
    href: '/catalog?category=stem',
    internal: true,
  })
})

test('a bare site path becomes an in-app link', () => {
  const parts = parseInline('Open /cart to continue', ORIGIN)
  assert.deepEqual(parts[1], { kind: 'link', text: '/cart', href: '/cart', internal: true })
})

test('a path that only starts like a route is not linked', () => {
  assert.deepEqual(parseInline('the /carton is here', ORIGIN), [text('the /carton is here')])
})

test('an external URL opens externally', () => {
  const parts = parseInline('Docs: https://example.com/page', ORIGIN)
  assert.deepEqual(parts[1], {
    kind: 'link',
    text: 'https://example.com/page',
    href: 'https://example.com/page',
    internal: false,
  })
})

test('a same-origin URL for a non-site route is external, not in-app', () => {
  const parts = parseInline('http://localhost:5173/admin', ORIGIN)
  assert.equal(parts[0].kind, 'link')
  assert.equal(parts[0].internal, false)
})

test('javascript: links stay plain text', () => {
  const input = '[click](javascript:alert(1))'
  assert.deepEqual(parseInline(input, ORIGIN), [text(input)])
})

test('HTML tags stay plain text', () => {
  const input = '<script>alert(1)</script><img src=x onerror=alert(1)>'
  assert.deepEqual(parseInline(input, ORIGIN), [text(input)])
})

test('a 5,000 character unbroken string parses without trouble', () => {
  const input = 'a'.repeat(5000)
  assert.deepEqual(parseInline(input, ORIGIN), [text(input)])
})

test('paragraphs are split on blank lines and keep single line breaks', () => {
  const blocks = parseReply('First line\nSecond line\n\nNext paragraph', ORIGIN)
  assert.equal(blocks.length, 2)
  assert.equal(blocks[0].kind, 'paragraph')
  assert.equal(blocks[0].lines.length, 2)
  assert.equal(blocks[1].kind, 'paragraph')
})

test('numbered lines become an ordered list', () => {
  const blocks = parseReply('Steps:\n1. Add toys\n2. Open the cart\n3) Pay', ORIGIN)
  assert.equal(blocks[0].kind, 'paragraph')
  assert.equal(blocks[1].kind, 'ordered')
  assert.equal(blocks[1].items.length, 3)
  assert.deepEqual(blocks[1].items[0], [text('Add toys')])
})

test('dash and bullet lines become a bullet list', () => {
  const blocks = parseReply('- one\n• two', ORIGIN)
  assert.equal(blocks.length, 1)
  assert.equal(blocks[0].kind, 'bullets')
  assert.equal(blocks[0].items.length, 2)
})

test('empty or whitespace input gives no blocks', () => {
  assert.deepEqual(parseReply('', ORIGIN), [])
  assert.deepEqual(parseReply('  \n \n', ORIGIN), [])
})

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
