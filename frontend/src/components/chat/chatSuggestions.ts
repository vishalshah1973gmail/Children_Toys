// Suggested questions. Every one of these is answered by the knowledge base
// (they come from docs/chatbot-kb/test-questions.md). No imports: Node tests run this directly.

export const STARTER_QUESTIONS = [
  'How much is shipping?',
  'How do I check out as a guest?',
  'Which test card can I use?',
  'How do I find toys for a 4-year-old?',
]

const TOPICS: { pattern: RegExp; questions: string[] }[] = [
  {
    pattern: /shipping|tax|total/i,
    questions: [
      'How much tax will I pay?',
      'What is the total for a $30.00 order?',
      'How do I check out as a guest?',
    ],
  },
  {
    pattern: /guest|checkout|card|payment|expir/i,
    questions: [
      'Which test card can I use?',
      'Will my card really be charged?',
      'Will I see my order in my order history after guest checkout?',
    ],
  },
  {
    pattern: /cart/i,
    questions: [
      'Do I need an account to add things to the cart?',
      'How much is shipping?',
      'How do I check out as a guest?',
    ],
  },
  {
    pattern: /password|sign in|account|username/i,
    questions: [
      'What are the password rules for a new account?',
      'Can I sign in with my email address?',
      'What happens to my guest cart when I sign in?',
    ],
  },
  {
    pattern: /age|stock|catalogue|catalog|toy/i,
    questions: [
      'How do I find toys for a 4-year-old?',
      'How do I show only toys that are in stock?',
      'How much is shipping?',
    ],
  },
  {
    pattern: /order|receipt|feedback|refund|return/i,
    questions: [
      'Where do I send feedback or a complaint?',
      'What is your returns policy?',
      'Will I see my order in my order history after guest checkout?',
    ],
  },
]

const GENERIC = [
  'How much is shipping?',
  'How do I check out as a guest?',
  'Where do I send feedback or a complaint?',
]

/** Up to three questions related to the topic just discussed, never repeating an asked one. */
export function followUpQuestions(userQuestion: string, reply: string, asked: string[]): string[] {
  const seen = new Set(asked.map((question) => question.trim().toLowerCase()))
  const result: string[] = []
  const add = (question: string) => {
    const key = question.toLowerCase()
    if (result.length < 3 && !seen.has(key)) {
      seen.add(key)
      result.push(question)
    }
  }
  const haystack = `${userQuestion} ${reply}`
  for (const topic of TOPICS) {
    if (topic.pattern.test(haystack)) topic.questions.forEach(add)
  }
  GENERIC.forEach(add)
  STARTER_QUESTIONS.forEach(add)
  return result
}
