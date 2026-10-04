# ToyBox Shopper Chatbot — Design

Date: 2026-10-04
Status: Draft, awaiting review

## Goal

Add a chat widget to the ToyBox site that answers shopper questions. Answers come from a Lyzr agent that retrieves from a Lyzr vector knowledge base. This spec covers (1) the knowledge pack that gets ingested and (2) the chat interface that talks to the agent.

## Decisions (agreed with Vishal)

| Topic | Decision |
|---|---|
| Audience and scope | Shoppers. Site how-to, policies, and the product catalogue. No personal or order data. |
| Product data freshness | One-time static ingest. Export is a re-runnable script so a refresh is one command later. Bot states that prices and stock are a snapshot. |
| Documenting the site | Source code, README and API read, plus a Playwright crawl of the running site. Code is the source of truth for facts; the crawl supplies customer-facing wording. |
| Lyzr integration | Backend proxy. Browser never sees the Lyzr key. |

## Out of scope

- Order lookup, account data, or any authenticated chat.
- Live product or stock calls from the agent.
- Admin pages, which are excluded from the crawl and from the knowledge base.
- Chat history persistence on the server.

## Part 1 — Knowledge pack

Location: `docs/chatbot-kb/`. One topic per file so each retrieved chunk is self-contained. Each file opens with a header (title, topic, source page/route). Headings are phrased as customer questions or tasks.

Files:

- `00-store-overview.md` — what ToyBox is, page map, demo/test-mode caveat.
- `01-browsing-catalogue.md` — categories, search, filters, product pages.
- `02-cart.md`
- `03-guest-checkout.md` — steps, card validation rules, receipt email, that it is not a real Stripe charge.
- `04-account-checkout.md` — register, login, Stripe test card, orders.
- `05-shipping-tax-pricing.md` — from `services/pricing.py`, exact numbers.
- `06-orders-and-receipts.md`
- `07-feedback.md`
- `08-policies-and-limits.md` — stock behaviour and what the bot cannot help with.
- `products.md` — generated from the DB by a script, one block per product: name, category, price in dollars, description, stock status, URL. Includes a "snapshot as of" date.
- `test-questions.md` — golden question list with expected answer sources.

Raw crawl notes go in `docs/chatbot-kb/_crawl/` and are not ingested.

### Crawl

Playwright walks: home, catalogue, a product page, cart, guest checkout, register, login, feedback, 404. Per page it records visible text, buttons, form fields and validation messages. Notes are cross-checked against the code before final docs are written. Authenticated and admin pages are read from code only.

### Product export

A script under `backend/scripts/` reads `Product` and `Category` through the existing session and writes `products.md`. It converts cents to a display price in one place and reuses no pricing logic beyond that.

### Ingest

The user creates the Lyzr agent and knowledge base in the Lyzr UI and uploads the files. Chunk by markdown heading. The agent system prompt instructs it to answer only from the knowledge base, say it does not know otherwise, and point to the Feedback page for anything unresolved.

## Part 2 — Chat interface

### Backend

`POST /api/chat`, body `{message: string, session_id: string}`, response `{reply: string}`.

- Calls the Lyzr inference API using `LYZR_API_KEY` and `LYZR_AGENT_ID` from `backend/.env`; both added to `.env.example` and the Render Blueprint as `sync: false`.
- Message length cap and per-client rate limit.
- Lyzr failure or timeout returns a friendly fallback message and a non-500 status the widget can handle. Errors are logged, never swallowed silently.
- Lives in a new router and a small service module, following the existing `routers/` and `services/` layout. No auth required.

### Frontend

`ChatWidget` component mounted in the main layout, hidden on `/admin/*`. Floating bubble, open/close panel, message list, input, typing indicator, error state. Styled to match ToyBox. `session_id` is generated once and kept in localStorage (wrapped in try/catch). An Axios call goes through the existing API client. Money is never formatted in the widget; the agent's text is displayed as returned.

## Verification

- pytest for `/api/chat` with Lyzr mocked: success, empty message, over-length, Lyzr error, rate limit.
- `npm run typecheck` and `npm run build` clean.
- Playwright pass: open widget, ask the golden questions, confirm answers match the docs.
- The golden list is reusable in the Lyzr playground before the widget is wired.

## Build order

1. Crawl and read the code.
2. Write the docs and the product export script.
3. User ingests into Lyzr and sets the agent prompt.
4. Backend proxy.
5. Widget.
6. End-to-end test.

Each step is reported before the next. Nothing is committed or pushed without explicit approval. No new packages are installed without approval; `httpx` is used only if already in `requirements.txt`.

## Risks

- Catalogue goes stale after a static ingest. Mitigation: re-runnable export script and the snapshot disclaimer.
- The deployed Render free tier sleeps, so the first chat request after idle may be slow. The widget shows a typing indicator and a long enough timeout.
- Lyzr API shape and auth header must be confirmed against current Lyzr docs before step 4.
