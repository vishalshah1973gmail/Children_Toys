import { api } from './client'

export async function sendChatMessage(message: string, sessionId: string): Promise<string> {
  // Must exceed the backend's Lyzr timeout (45s) plus a possible Render cold start.
  const response = await api.post<{ reply: string }>(
    '/chat',
    { message, session_id: sessionId },
    { timeout: 60000 },
  )
  return response.data.reply
}
