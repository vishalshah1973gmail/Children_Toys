import assert from 'node:assert/strict'
import test from 'node:test'

import { STARTER_QUESTIONS, followUpQuestions } from '../src/components/chat/chatSuggestions.ts'

test('there are four starter questions', () => {
  assert.equal(STARTER_QUESTIONS.length, 4)
})

test('a shipping answer suggests tax and totals', () => {
  const result = followUpQuestions('How much is shipping?', 'Shipping is $5.99 under $50.', [
    'How much is shipping?',
  ])
  assert.equal(result.length, 3)
  assert.ok(result.includes('How much tax will I pay?'))
})

test('already asked questions are never suggested again', () => {
  const asked = ['How much tax will I pay?', 'What is the total for a $30.00 order?']
  const result = followUpQuestions('How much is shipping?', 'Shipping is $5.99.', asked)
  for (const question of asked) assert.ok(!result.includes(question))
})

test('unrelated text still gets three suggestions', () => {
  const result = followUpQuestions('zzz', 'qqq', [])
  assert.equal(result.length, 3)
})

test('suggestions have no duplicates', () => {
  const result = followUpQuestions('checkout card payment', 'guest checkout card cart', [])
  assert.equal(new Set(result).size, result.length)
})

test('matching is case-insensitive', () => {
  const upper = followUpQuestions('PASSWORD', 'SIGN IN WITH YOUR USERNAME', [])
  assert.ok(upper.includes('Can I sign in with my email address?'))
})
