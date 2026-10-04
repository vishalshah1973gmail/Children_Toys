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
        text: 'http://localhost:5173/product/castle-quest-brick-set',
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
    text: 'https://toybox.example/catalog?category=stem',
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
