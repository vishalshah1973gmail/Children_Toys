# ToyBox Chat Interface Enhancements — Design

Date: 2026-10-04
Status: Draft, awaiting review
Builds on: `2026-10-04-chatbot-design.md` (the chatbot itself is built and working on branch `chatbot-feature`).

## Goal

Make the chat widget look and feel like a finished product, and make its answers more useful: a friendlier font, a polished layout, clickable and well-formatted replies, suggested questions, small reply tools, and product cards that show live price and stock for any toy the assistant mentions.

## Decisions (agreed with Vishal)

| Topic | Decision |
|---|---|
| Font | Nunito, in the chat only. Loaded from Google Fonts; the rest of the site keeps its current look. |
| Visual polish | Full: bot avatar, refined bubbles and spacing, header with a status line, bouncing-dots typing indicator, timestamps, smoother open animation. |
| Extras | All four: starter and follow-up chips; links and formatting in replies; copy, new chat and thumbs up/down; product cards in answers. |
| Product cards | Server-side name matching against the live database. No change to the Lyzr agent or its prompt. |
| Chips | Deterministic: a fixed starter list, and follow-ups chosen from a small topic table in the widget. The agent does not generate them. |
| Thumbs up/down | Stored in the browser only. Nothing is sent to the backend. |

## Out of scope

- Any change to the Lyzr agent, its instructions, or the knowledge base.
- Streaming replies, cart-aware tips ("add $12 for free shipping"), sending thumbs feedback to the server, saving conversations across page reloads, full markdown support (headings, tables, code), translations.
- Changing fonts anywhere outside the chat.

## Part 1 — Backend: product cards

The chat response gains a list of products mentioned in the reply. Existing clients keep working because the new field defaults to an empty list.

### Response shape

`POST /api/chat` returns `{ "reply": string, "products": ChatProduct[] }`.

`ChatProduct` fields, all taken from the database at request time:

- `slug` (string), `name` (string), `brand` (string), `category_name` (string)
- `price_cents` (integer; the widget formats it with the existing `formatMoney`)
- `in_stock` (boolean; true when the stock quantity is above zero. The quantity itself is not sent.)
- `min_age_months`, `max_age_months` (integers; the widget formats them with `formatAgeRange`)
- `image_url` (string or null; the primary image path, which the widget turns into an absolute URL with the existing `assetUrl`)

### Matching rules (new service module `chat_products.py`)

`find_mentioned_products(db, reply) -> list[Product]`:

1. Consider active products only (`is_active` true). Out-of-stock products are included and flagged, because "this toy is sold out" is useful to a shopper.
2. A product matches when its name appears in the reply, case-insensitively. The name is also matched without a trailing parenthetical, so "Rainbow Rise Wooden Block Set (100 pieces)" matches "Rainbow Rise Wooden Block Set". Curly and straight apostrophes and dashes are treated as equal. Aliases shorter than 6 characters are ignored so short names cannot match inside ordinary words.
3. Longer names are matched first, and a stretch of text already claimed by a match cannot be matched again, so one product name that contains another cannot produce two cards.
4. Results are ordered by where they first appear in the reply, each product at most once, and capped at 3 (`MAX_PRODUCT_CARDS`).
5. Only names and ids are read for matching; full rows (with images and category) are loaded only for the matched products.

### Failure behaviour

Cards are an enhancement. If the lookup raises, the router logs the error with `logger.exception` and returns the reply with `products: []`. The shopper still gets the answer. This is a deliberate exception to "surface errors", and it is logged. The Lyzr call, rate limiter, input validation and typed error bodies are unchanged. The lookup runs in a worker thread (`run_in_threadpool`) so the async endpoint does not block on the database.

## Part 2 — Frontend

### Files

| File | Responsibility |
|---|---|
| `frontend/index.html` (modify) | Preconnect and stylesheet link for Nunito (weights 400, 600, 700, 800). |
| `frontend/tailwind.config.js` (modify) | Add `fontFamily.chat`: Nunito, then the system sans-serif stack. |
| `frontend/src/index.css` (modify) | Keyframes for the typing dots and the panel open animation; both disabled under `prefers-reduced-motion`. |
| `frontend/src/types.ts` (modify) | `ChatProduct` type. |
| `frontend/src/api/chat.ts` (modify) | Return `{ reply, products }`. |
| `frontend/src/components/ChatWidget.tsx` (modify) | Shell and state: open/close, messages, send, new chat, session id. Mounted in Layout as today. |
| `frontend/src/components/chat/chatText.ts` (new) | Pure functions that turn reply text into blocks (paragraph, list) and inline pieces (text, bold, link). No React. |
| `frontend/src/components/chat/ChatMessageBody.tsx` (new) | Renders the parsed blocks as React elements. |
| `frontend/src/components/chat/ProductCard.tsx` (new) | One product card. |
| `frontend/src/components/chat/SuggestionChips.tsx` (new) | A row of clickable question chips. |
| `frontend/src/components/chat/chatSuggestions.ts` (new) | The starter list and the topic table that picks follow-ups. |
| `frontend/src/components/chat/MessageActions.tsx` (new) | Copy and thumbs up/down for one bot message. |

### Font

Nunito is applied by a `font-chat` class on the chat root, so only chat text uses it. Buttons and inputs already inherit the font. If Google Fonts is blocked the chat falls back to the system sans-serif and stays usable. This adds a third-party request to Google; it happens only when chat text is first drawn, because the browser downloads a web font on first use.

### Visual design (uses the existing orange `brand` and slate `ink` tokens)

- Panel about 22rem wide (capped to the viewport), height `min(36rem, 100dvh - 6rem)`, rounded corners, soft shadow, warm off-white background.
- Header: brand gradient, round white avatar with a small toy-block/smile icon, title "ToyBox assistant", and a status line with a green dot reading "Here to help". It states no response-time claim.
- User bubbles: right-aligned, brand colour, white text, tail corner bottom-right. Bot bubbles: left-aligned, white with a thin border, tail corner bottom-left, with the avatar beside the first bot bubble of a run. Message text 15px with 1.5 line height.
- Timestamp under each bubble, small and muted, formatted with the browser's locale (for example "10:42 AM").
- Typing indicator: three bouncing dots in a bot bubble.
- Opening: a short scale-and-fade animation. The launcher icon button stays as built.
- Input row: rounded pill input and a round send button with an arrow icon, still disabled while a reply is pending or the draft is blank.
- Small inclusions that came with the polish: focus moves to the input when the panel opens, and Escape closes it.

### Reply formatting (`chatText.ts`)

Replies are plain text from the agent. The formatter supports only:

- Paragraphs separated by blank lines; single line breaks are kept.
- Lists: consecutive lines starting with `1.`, `2.` … become an ordered list; lines starting with `-` or `•` become a bullet list.
- `**bold**`.
- Links. Allowed targets only: an `http://` or `https://` URL, or a path matching the site's own routes (`/catalog`, `/cart`, `/login`, `/register`, `/feedback`, `/orders`, `/account`, `/checkout/guest`, `/product/<slug>`). A full URL whose origin equals the site's origin, or the old `localhost` address used in the product file, is converted to an in-app link (client-side navigation); other URLs open in a new tab with `rel="noopener noreferrer"`.

Nothing is ever inserted as HTML. Text is rendered as React text nodes, and any other URL scheme (`javascript:`, `data:` and so on) stays plain text.

### Product cards (`ProductCard.tsx`)

Shown under the bot bubble that mentioned them: image (with an empty-image fallback), name, brand, price via `formatMoney`, an "In stock" or "Out of stock" label (stock quantity is not shown, to avoid stale-number claims), age range via `formatAgeRange`, and a "View" button that goes to `/product/<slug>`. Because cards come from the database, they show current prices even though the text of the answer may quote a snapshot.

### Chips (`SuggestionChips.tsx`, `chatSuggestions.ts`)

- Starter chips: four questions shown under the greeting when the chat is empty of user messages, for example "How much is shipping?" and "How do I check out as a guest?". They disappear after the first user message.
- Follow-up chips: after each bot reply, up to 3 chips are chosen from a topic table by matching keywords in the user's question and the reply (checkout, shipping and tax, cart, account, products, orders). If nothing matches, a generic set is used. All suggested questions are ones the knowledge base answers (they come from `docs/chatbot-kb/test-questions.md`).
- Clicking a chip sends it as the user's message. Chips are hidden while a reply is pending.

### Reply tools (`MessageActions.tsx`)

- Copy: copies the reply text to the clipboard and shows "Copied" briefly. If the clipboard is unavailable the button does nothing visible and the app does not error.
- Thumbs up/down: one choice per reply, toggleable, saved in `localStorage` under `toybox.chat_feedback` keyed by a message id; reads and writes are wrapped in try/catch, so blocked storage only means the choice is not remembered. Nothing is sent to the server.
- New chat: a header button that clears the conversation, restores the greeting and starter chips, and starts a new Lyzr session id (so the agent forgets the old conversation).

### State and data flow

`ChatWidget` holds `messages` (each with an id, role, text, timestamp and, for bot messages, `products`), `pending` and `error`, as today. Sending calls `sendChatMessage` and appends the reply and its products. The double-submit guard and session-id logic from the existing widget are kept.

## Error handling

- Backend errors (503, 429, 422) are shown exactly as today, in an alert under the messages.
- A failed product lookup only removes cards (see Part 1).
- A reply with no recognisable formatting renders as plain paragraphs.

## Testing

Backend (pytest, Lyzr mocked as in the existing tests):

- Matching: plain name; name without its parenthetical; different letter case; curly versus straight apostrophe; more than 3 products capped at 3; order of first appearance; the same product named twice appears once; a name that contains another name produces one card; inactive product excluded; out-of-stock product included with `in_stock` false; a product with no image gives `image_url` null; reply with no product gives `[]`.
- Endpoint: response includes `products` with the expected fields; when the lookup is made to raise, the reply is still returned with `products: []` and an error is logged; existing tests still pass unchanged.

Frontend (no test runner exists, and none is added): `npm run typecheck` and `npm run build`, plus a browser pass with Playwright using request interception to return crafted replies from `/api/chat`:

- Formatting: bold, numbered list, bullet list, an in-app link, an external link opening in a new tab, and a `javascript:` link staying plain text.
- Cards: three cards render with image, formatted price, stock label, age range and a working View button; an out-of-stock card is labelled.
- Chips: starters appear on open and vanish after the first message; a follow-up chip sends its question; chips are hidden while pending.
- Tools: copy shows "Copied"; a thumbs choice survives a page reload; New chat resets the conversation.
- Layout and access: 375px wide screen, keyboard order and Escape, reduced-motion setting disables the animations, the font really is Nunito (computed style), and the console shows no new errors.
- A final live check with the real agent: a product question produces cards with current prices.

## Review focus (failure modes the tests above must cover)

1. A reply that mentions a product only by a shortened or differently cased name must still produce its card; one that mentions no product must produce none.
2. A product lookup failure must never cost the shopper their answer.
3. Hostile or odd reply text (HTML tags, `javascript:` links, very long unbroken strings, empty lines) must render safely and without breaking the layout.
4. Blocked localStorage or clipboard must not break chat (the existing site-wide localStorage limitation in the API client is unchanged and out of scope).
5. Rapid clicking on a chip while a reply is pending must not send twice.

## Documentation

Update the Chatbot subsection of `CLAUDE.md` and README section 13 with the new response shape, the matching rules, and the new files.
