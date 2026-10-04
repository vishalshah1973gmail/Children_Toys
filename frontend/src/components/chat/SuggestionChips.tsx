interface SuggestionChipsProps {
  questions: string[]
  onPick: (question: string) => void
}

export default function SuggestionChips({ questions, onPick }: SuggestionChipsProps) {
  if (questions.length === 0) return null
  return (
    <div className="flex flex-wrap gap-2" aria-label="Suggested questions">
      {questions.map((question) => (
        <button
          key={question}
          type="button"
          onClick={() => onPick(question)}
          className="rounded-full border border-brand-300 bg-white px-3 py-1.5 text-left text-sm font-semibold text-brand-700 hover:bg-brand-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500"
        >
          {question}
        </button>
      ))}
    </div>
  )
}
