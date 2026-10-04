import type { ChatProduct } from '../types'
import { api } from './client'

export interface ChatReply {
  reply: string
  products: ChatProduct[]
}

export async function sendChatMessage(message: string, sessionId: string): Promise<ChatReply> {
  // Must exceed the backend's Lyzr timeout (45s) plus a possible Render cold start.
  const response = await api.post<{ reply: string; products?: ChatProduct[] }>(
    '/chat',
    { message, session_id: sessionId },
    { timeout: 60000 },
  )
  return { reply: response.data.reply, products: response.data.products ?? [] }
}
