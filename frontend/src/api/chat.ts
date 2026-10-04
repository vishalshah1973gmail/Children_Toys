import { api } from './client'

export async function sendChatMessage(message: string, sessionId: string): Promise<string> {
  const response = await api.post<{ reply: string }>('/chat', {
    message,
    session_id: sessionId,
  })
  return response.data.reply
}
