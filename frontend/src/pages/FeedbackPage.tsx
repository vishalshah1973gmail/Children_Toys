const FORM_URL = import.meta.env.VITE_N8N_FEEDBACK_FORM_URL as string | undefined

/** Embeds the n8n-hosted feedback form. n8n owns the fields and the submit flow. */
export default function FeedbackPage() {
  return (
    <div className="mx-auto my-auto w-full max-w-2xl py-8">
      <h1 className="font-display text-2xl text-ink-900">Feedback</h1>
      <p className="mt-2 text-ink-700">
        Tell us about your experience shopping with ToyBox.
      </p>

      {FORM_URL ? (
        <iframe
          src={FORM_URL}
          title="ToyBox feedback form"
          className="mt-6 h-[900px] w-full rounded-lg border border-ink-800/10"
        />
      ) : (
        <div className="mt-6 rounded-lg border border-ink-800/10 bg-orange-50 p-6 text-ink-700">
          Feedback form is not configured. Set VITE_N8N_FEEDBACK_FORM_URL in
          the frontend .env file.
        </div>
      )}
    </div>
  )
}
