import SplitPage from '../components/SplitPage'

const FORM_URL = import.meta.env.VITE_N8N_FEEDBACK_FORM_URL as string | undefined

/** Embeds the n8n-hosted feedback form. n8n owns the fields and the submit flow. */
export default function FeedbackPage() {
  return (
    <SplitPage
      eyebrow="We're listening"
      title="Feedback"
      subtitle="Tell us about your experience shopping with ToyBox."
    >
      {FORM_URL ? (
        <iframe
          src={FORM_URL}
          title="ToyBox feedback form"
          className="h-[80vh] min-h-[600px] w-full rounded-lg border border-ink-800/10"
        />
      ) : (
        <div className="rounded-lg border border-ink-800/10 bg-orange-50 p-6 text-lg text-ink-700">
          Feedback form is not configured. Set VITE_N8N_FEEDBACK_FORM_URL in
          the frontend .env file.
        </div>
      )}
    </SplitPage>
  )
}
