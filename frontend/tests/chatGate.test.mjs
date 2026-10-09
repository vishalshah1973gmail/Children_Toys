import assert from 'node:assert/strict'
import test from 'node:test'

import { CHAT_LOGIN_REQUIRED_MESSAGE } from '../src/components/chat/chatGate.ts'

test('the logged-out chat popup says exactly what was requested', () => {
  assert.equal(
    CHAT_LOGIN_REQUIRED_MESSAGE,
    'I am sorry I cannot respond to you till you register and log in. This is necessary to ensure that only validated people are allowed to use the Application & Chat.',
  )
})
