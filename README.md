# ToyBox — a full-stack children's toy store

A complete, runnable e-commerce application: React 18 + Vite + TypeScript on the
front, FastAPI + SQLAlchemy 2.x + SQLite on the back, Stripe Checkout in test
mode for payments, and a seeded catalogue of 24 toys plus a synthetic year of
2026 customer purchase history.

---

## 1. Architecture

```
Browser ──► React 18 SPA (Vite, Tailwind, Zustand, React Router)
              │  Axios, Bearer access token, auto-refresh on 401
              ▼
           FastAPI (Uvicorn) ── SQLAlchemy 2.x ORM ──► SQLite (app.db)
              │                                          Alembic migrations
              ├─► POST /api/checkout/session ──► Stripe Checkout (test mode)
              └─◄ POST /api/webhooks/stripe  ◄── Stripe signed webhook
```

* **Auth flow.** Register/login return a 30-minute JWT access token and a
  7-day refresh token. The Axios interceptor retries a 401 once after
  refreshing. Logout adds the refresh token's `jti` to a denylist. A `role`
  claim (`customer` / `admin`) is checked by the `get_current_admin`
  dependency on every `/api/admin/*` route.
* **Payment flow.** Checkout builds a **pending** order from the *server-side*
  cart, validating stock but changing nothing. Stripe prices the session from
  the order rows, never from the browser. Only the signature-verified webhook
  (`checkout.session.completed`, `payment_status == "paid"`) marks the order
  paid, decrements stock and empties the cart — and it is idempotent.

---

## 2. File tree

```
ECommerce_Website/
├── .env.example                 every environment variable, commented
├── .gitignore
├── docker-compose.yml           backend + frontend, one command
├── README.md
├── backend/
│   ├── Dockerfile
│   ├── .dockerignore
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── pytest.ini
│   ├── alembic/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/0001_initial_schema.py
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              FastAPI app, CORS, static mount, routers
│   │   ├── core/
│   │   │   ├── config.py        pydantic-settings configuration
│   │   │   ├── security.py      bcrypt hashing + JWT issue/decode
│   │   │   ├── deps.py          current user / admin dependencies
│   │   │   ├── errors.py        typed error envelope + handlers
│   │   │   └── utils.py         slugs, order numbers, age formatting
│   │   ├── db/
│   │   │   ├── base.py          DeclarativeBase + TimestampMixin
│   │   │   └── session.py       engine, SessionLocal, get_db
│   │   ├── models/
│   │   │   ├── user.py          users, UserRole
│   │   │   ├── token.py         revoked_tokens (logout denylist)
│   │   │   ├── category.py      categories
│   │   │   ├── product.py       products, product_images
│   │   │   ├── cart.py          cart_items
│   │   │   ├── order.py         orders, order_items, OrderStatus
│   │   │   └── payment.py       payments, PaymentStatus
│   │   ├── schemas/
│   │   │   ├── common.py        Page[T], ErrorDetail, Message
│   │   │   ├── user.py  category.py  product.py  cart.py  order.py
│   │   │   └── chat.py          chat request/response, ChatProduct card, 500-char cap
│   │   ├── services/
│   │   │   ├── pricing.py       shipping / tax / totals in integer cents
│   │   │   ├── cart_service.py  cart reads and mutations
│   │   │   ├── order_service.py order creation, payment confirmation
│   │   │   ├── stripe_service.py Checkout Session + signature verification
│   │   │   ├── chat_service.py  Lyzr agent proxy + per-client rate limiter
│   │   │   └── chat_products.py products named in a chat reply (for cards)
│   │   └── routers/
│   │       ├── auth.py  categories.py  products.py  cart.py
│   │       ├── orders.py  checkout.py  admin.py  chat.py
│   ├── scripts/
│   │   ├── catalog_data.py            5 categories + 24 toys
│   │   ├── generate_synthetic_data.py 2026 customers/orders → CSV
│   │   ├── export_kb_products.py      active products → chatbot knowledge-base markdown
│   │   └── seed.py                    loads everything into the database
│   ├── data/                    generated CSVs (products, customers, orders,
│   │                            order_items, payments)
│   ├── static/uploads/          product images on local disk
│   └── tests/
│       ├── conftest.py  test_auth.py  test_admin_access.py
│       ├── test_cart.py  test_checkout.py  test_chat.py  test_chat_products.py
├── docs/
│   └── chatbot-kb/              chatbot knowledge pack (docs 00-02 and 04-08, products.md,
│                                test-questions.md); _crawl/ is scratch, not ingested
└── frontend/
    ├── Dockerfile  nginx.conf  index.html  package.json
    ├── vite.config.ts  tsconfig.json  tailwind.config.js  postcss.config.js
    ├── .env.example  .dockerignore
    └── src/
        ├── main.tsx  App.tsx  index.css  types.ts  vite-env.d.ts
        ├── lib/format.ts
        ├── api/    client.ts  auth.ts  catalog.ts  cart.ts  orders.ts  admin.ts  chat.ts
        ├── store/  authStore.ts  cartStore.ts
        ├── components/
        │   Layout.tsx  Navbar.tsx  Footer.tsx  ProductCard.tsx
        │   CatalogFilters.tsx  Pagination.tsx  Spinner.tsx
        │   ErrorBanner.tsx  EmptyState.tsx  ProtectedRoute.tsx
        │   AdminRoute.tsx  AdminLayout.tsx  ChatWidget.tsx
        │   chat/  ChatMessageBody.tsx  ProductCard.tsx  SuggestionChips.tsx
        │          MessageActions.tsx  chatText.ts  chatSuggestions.ts
        └── pages/
            HomePage  CatalogPage  ProductDetailPage  CartPage
            CheckoutPage  CheckoutSuccessPage  CheckoutCancelPage
            OrdersPage  OrderDetailPage  AccountPage
            LoginPage  RegisterPage  NotFoundPage
            admin/ AdminOverviewPage  AdminProductsPage  ProductFormModal
                   AdminCategoriesPage  AdminOrdersPage
```

---

## 3. Database schema

All money is stored as **integer cents**. All ages are stored in **months**.

### users
| Column | Type | Notes |
|---|---|---|
| id | INTEGER | PK |
| username | VARCHAR(50) | unique, indexed |
| email | VARCHAR(255) | unique, indexed |
| full_name | VARCHAR(120) | nullable |
| hashed_password | VARCHAR(255) | bcrypt, never plaintext |
| role | ENUM(customer, admin) | indexed, default `customer` |
| is_active | BOOLEAN | default true |
| approval_status | VARCHAR(20) | `pending` / `approved` / `rejected`, indexed; migration `0003_user_approval` backfills existing users as `approved` |
| rejection_reason | VARCHAR(500) | nullable, set when an admin rejects |
| reviewed_at | TIMESTAMP | nullable, when an admin last reviewed the registration |
| created_at / updated_at | TIMESTAMP | |

### revoked_tokens
| Column | Type | Notes |
|---|---|---|
| id | INTEGER | PK |
| jti | VARCHAR(64) | unique, indexed |
| user_id | INTEGER | FK → users.id ON DELETE CASCADE |
| expires_at | TIMESTAMP | |

### categories
| Column | Type | Notes |
|---|---|---|
| id | INTEGER | PK |
| name | VARCHAR(120) | unique |
| slug | VARCHAR(140) | unique, indexed |
| description | TEXT | nullable |
| image_url | VARCHAR(500) | nullable |

### products
| Column | Type | Notes |
|---|---|---|
| id | INTEGER | PK |
| name | VARCHAR(200) | indexed |
| slug | VARCHAR(220) | unique, indexed |
| description | TEXT | |
| price_cents | INTEGER | CHECK ≥ 0 |
| stock_quantity | INTEGER | CHECK ≥ 0 |
| category_id | INTEGER | FK → categories.id ON DELETE RESTRICT, indexed |
| min_age_months / max_age_months | INTEGER | CHECK min ≤ max |
| brand | VARCHAR(120) | indexed |
| safety_notes | TEXT | nullable |
| is_featured | BOOLEAN | indexed |
| is_active | BOOLEAN | composite index (category_id, is_active) |

### product_images
| Column | Type | Notes |
|---|---|---|
| id | INTEGER | PK |
| product_id | INTEGER | FK → products.id ON DELETE CASCADE, indexed |
| url | VARCHAR(500) | path under `/static/uploads/` |
| alt_text | VARCHAR(255) | nullable |
| sort_order | INTEGER | |
| is_primary | BOOLEAN | |

### cart_items
| Column | Type | Notes |
|---|---|---|
| id | INTEGER | PK |
| user_id | INTEGER | FK → users.id CASCADE, indexed |
| product_id | INTEGER | FK → products.id CASCADE, indexed |
| quantity | INTEGER | CHECK > 0 |
| — | — | UNIQUE (user_id, product_id) |

### orders
| Column | Type | Notes |
|---|---|---|
| id | INTEGER | PK |
| order_number | VARCHAR(32) | unique, indexed, e.g. `TB-20260906-4F7QK2` |
| user_id | INTEGER | FK → users.id RESTRICT, indexed |
| status | ENUM(pending, paid, shipped, delivered, cancelled) | indexed |
| subtotal_cents / shipping_cents / tax_cents / total_cents | INTEGER | |
| currency | VARCHAR(3) | |
| contact_email | VARCHAR(255) | |
| shipping_name / line1 / line2 / city / state / postal_code / country | VARCHAR | |
| stripe_session_id | VARCHAR(255) | indexed |
| placed_at / paid_at / shipped_at / delivered_at | TIMESTAMP | nullable |

### order_items
| Column | Type | Notes |
|---|---|---|
| id | INTEGER | PK |
| order_id | INTEGER | FK → orders.id CASCADE, indexed |
| product_id | INTEGER | FK → products.id RESTRICT, indexed |
| product_name / product_slug / image_url | VARCHAR | frozen snapshot at order time |
| unit_price_cents / quantity / line_total_cents | INTEGER | CHECK quantity > 0 |

### payments
| Column | Type | Notes |
|---|---|---|
| id | INTEGER | PK |
| order_id | INTEGER | FK → orders.id CASCADE, indexed |
| provider | VARCHAR(40) | `stripe`, `manual`, `dev` |
| stripe_session_id / stripe_payment_intent_id | VARCHAR(255) | indexed |
| stripe_event_id | VARCHAR(255) | unique — makes webhook replay a no-op |
| amount_cents / currency | INTEGER / VARCHAR(3) | |
| status | ENUM(pending, succeeded, failed, refunded) | indexed |
| failure_reason | TEXT | nullable |

**Relationships.** `users 1─* cart_items *─1 products`,
`categories 1─* products 1─* product_images`,
`users 1─* orders 1─* order_items *─1 products`, `orders 1─* payments`.

---

## 4. API contract

Base path `/api`. Auth is a `Bearer <access_token>` header.

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/health` | — | Liveness probe (no `/api` prefix) |
| POST | `/auth/register` | — | Create a `pending` customer account; returns `{status: "pending", message}` and no tokens (an admin must approve it; a rejected account can re-register with the same username and email) |
| POST | `/auth/login` | — | Exchange username + password for tokens; 403 `approval_pending` / `registration_rejected` until approved |
| POST | `/auth/refresh` | — | Swap a refresh token for a new pair |
| POST | `/auth/logout` | — | Revoke a refresh token |
| GET | `/auth/me` | user | The signed-in user |
| POST | `/auth/change-password` | user | Change own password |
| GET | `/categories` | — | All categories with product counts |
| GET | `/categories/{slug}` | — | One category |
| GET | `/products` | — | Catalog: `q`, `category`, `min_price_cents`, `max_price_cents`, `age_months`, `brand`, `featured`, `in_stock`, `sort`, `page`, `page_size` |
| GET | `/products/featured` | — | Home-page toys |
| GET | `/products/brands` | — | Distinct brands for the filter panel |
| GET | `/products/{slug}` | — | One product with images |
| GET | `/cart` | user | Cart with server-computed totals |
| POST | `/cart/items` | user | Add a product (409 if over stock) |
| PATCH | `/cart/items/{id}` | user | Set a line quantity |
| DELETE | `/cart/items/{id}` | user | Remove a line |
| DELETE | `/cart` | user | Empty the cart |
| POST | `/cart/merge` | user | Fold a guest cart in after sign-in |
| POST | `/checkout/session` | user | Create the pending order + Stripe session |
| POST | `/checkout/dev-confirm/{order_number}` | user | Local confirm when Stripe is unconfigured |
| POST | `/webhooks/stripe` | Stripe signature | Confirm payment, decrement stock |
| POST | `/chat` | user | Shopper chatbot (signed-in approved users only): `{message, session_id}` → `{reply, products}` (up to 3 live product cards); 401 `not_authenticated`, 429 `rate_limited`, 503 `chat_not_configured` / `chat_unavailable` |
| GET | `/orders` | user | Own order history, paginated |
| GET | `/orders/{order_number}` | user | Own order (admins may read any) |
| GET | `/admin/stats` | admin | Dashboard headline numbers, including `pending_approvals` |
| GET | `/admin/registrations` | admin | Registrations, filterable by `status` (default pending) |
| POST | `/admin/registrations/{id}/approve` | admin | Approve a registration and email the applicant |
| POST | `/admin/registrations/{id}/reject` | admin | Reject with a required `reason` and email the applicant; 409 `already_reviewed` if already decided |
| GET | `/admin/products` | admin | All products, inactive included |
| POST | `/admin/products` | admin | Create a product |
| PATCH | `/admin/products/{id}` | admin | Edit a product (and its images) |
| PATCH | `/admin/products/{id}/stock` | admin | `set_to` or `delta` |
| DELETE | `/admin/products/{id}` | admin | Delete, or deactivate if ordered before |
| POST | `/admin/uploads/images` | admin | Upload an image to local disk |
| POST | `/admin/categories` | admin | Create a category |
| PATCH | `/admin/categories/{id}` | admin | Edit a category |
| DELETE | `/admin/categories/{id}` | admin | Delete an empty category |
| GET | `/admin/orders` | admin | All orders, filterable by status |
| PATCH | `/admin/orders/{order_number}/status` | admin | pending → paid → shipped → delivered |
| GET | `/admin/users` | admin | All accounts |

Every failure returns the same shape:

```json
{ "error": { "code": "insufficient_stock", "message": "Only 2 of 'Castle Quest Brick Set' left in stock", "field": "quantity" } }
```

---

## 5. Prerequisites

* Python 3.11+ (3.10 works)
* Node.js 20+ and npm
* Optional: Docker + Docker Compose, and the Stripe CLI for webhook testing

---

## 6. Setup — run it locally

Run these **in order**.

### 6.1 Backend

```bash
cd backend

python -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows PowerShell
# .venv\Scripts\Activate.ps1

pip install -r requirements.txt

# Configuration: copy the root example and edit as needed
cp ../.env.example .env          # Windows: copy ..\.env.example .env
```

At minimum set `JWT_SECRET_KEY` to a long random string. Leave
`STRIPE_SECRET_KEY` blank for now — the app runs without Stripe (see §9).

**Run the migrations:**

```bash
alembic upgrade head
```

**Run the seed script** (categories, 24 toys, placeholder images, two logins,
and the synthetic 2026 history):

```bash
python -m scripts.seed
```

Useful variants:

```bash
python -m scripts.seed --reset          # drop and recreate every table first
python -m scripts.seed --no-synthetic   # catalogue and the two logins only
python -m scripts.seed --regenerate     # regenerate the CSVs, then load them
```

**Start the API:**

```bash
uvicorn app.main:app --reload --port 8000
```

Interactive docs: <http://localhost:8000/docs>

### 6.2 Frontend

In a second terminal:

```bash
cd frontend
npm install
cp .env.example .env             # Windows: copy .env.example .env
npm run dev
```

Storefront: <http://localhost:5173>

---

## 7. Running the tests

```bash
cd backend
pytest              # or: python -m pytest -v
```

The chat widget's pure logic (reply parsing and suggestion chips) has its own
tests, run with Node's built-in runner and no extra packages:

```bash
cd frontend
node --test         # Node 24; give it no directory argument (naming the directory fails)
```

It runs `tests/chatText.test.mjs`, `tests/chatSuggestions.test.mjs` and `tests/chatGate.test.mjs`. On the
backend, `test_chat.py` covers the endpoint and `test_chat_products.py` covers
the product matching.

Each test gets its own throwaway SQLite file, so tests never touch `app.db`.
Coverage includes registration, login with the wrong password, an admin route
blocked for a customer, add-to-cart, and checkout rejected on insufficient
stock — plus refresh-token revocation, server-side pricing, and the rule that
stock only moves when payment is confirmed.

---

## 8. Testing Stripe locally

The backend has two payment modes.

**Dev mode (no Stripe keys).** With `STRIPE_SECRET_KEY` blank and
`ALLOW_DEV_PAYMENT=true`, checkout skips Stripe and the frontend calls
`POST /api/checkout/dev-confirm/{order_number}`, which runs exactly the same
confirmation path the webhook does. Useful for exercising the whole flow before
you have any keys.

**Stripe test mode.**

1. Put your test keys in `backend/.env`:

   ```
   STRIPE_SECRET_KEY=sk_test_...
   ```

2. Install the [Stripe CLI](https://stripe.com/docs/stripe-cli) and log in:

   ```bash
   stripe login
   ```

3. Forward webhooks to the running backend:

   ```bash
   stripe listen --forward-to localhost:8000/api/webhooks/stripe
   ```

4. Copy the `whsec_...` signing secret the CLI prints into `backend/.env` as
   `STRIPE_WEBHOOK_SECRET`, then restart Uvicorn.

5. Check out in the storefront and pay with the test card
   **4242 4242 4242 4242**, any future expiry, any CVC, any ZIP.

6. Watch the CLI: `checkout.session.completed` should return `200`, the order
   flips to **paid**, and stock drops. You can also replay it by hand:

   ```bash
   stripe trigger checkout.session.completed
   ```

A webhook with a missing or invalid signature is rejected with `400`; with no
`STRIPE_WEBHOOK_SECRET` configured at all it returns `503`.

### Registration approval settings

New accounts wait for admin approval, and emails use the existing `SMTP_*`
settings. Two more variables in `backend/.env` (see `backend/.env.example`):

```
ADMIN_NOTIFY_EMAIL=   # where new-registration alerts go; blank = first admin user's email
FRONTEND_BASE_URL=http://localhost:5173   # base of the sign-in link in approval emails
```

Emails are best-effort: a failure is logged and never fails the request.

### Chatbot keys

The shopper chat widget needs two more variables in `backend/.env` (they are
listed in `backend/.env.example`, and in `render.yaml` as `sync: false`
secrets):

```
LYZR_API_KEY=...      # Lyzr API key, server-side only
LYZR_AGENT_ID=...     # agent id from Lyzr Studio
```

Leave them blank and `POST /api/chat` returns `503 chat_not_configured`; the
rest of the store is unaffected. See §13 for the chatbot itself.

---

## 9. Docker

```bash
docker compose up --build
docker compose exec backend python -m scripts.seed
```

* Storefront: <http://localhost:5173>
* API: <http://localhost:8000>

Migrations run automatically on backend start. The SQLite file and uploaded
images live on named volumes, so they survive `docker compose down` (and are
removed by `down -v`).

---

## 10. The synthetic 2026 dataset

`python -m scripts.generate_synthetic_data` writes five CSVs into
`backend/data/`. The generator is deterministic — seed `2026` — so regenerating
reproduces exactly the same numbers.

| File | Rows | Contents |
|---|---|---|
| `products.csv` | 24 | Catalogue reference: slug, category, brand, price, age band |
| `customers.csv` | 50 | Username, email, signup date, city/state, children, acquisition channel |
| `orders.csv` | 200 | Order number, customer, status, timestamps, subtotal/shipping/tax/total, channel, ship-to |
| `order_items.csv` | ~390 | Product, brand, category, unit price, quantity, line total |
| `payments.csv` | ~190 | One succeeded payment per non-cancelled order |

Shape of the data:

* Every order falls in **January–December 2026**, weighted for real toy-retail
  seasonality: a quiet spring, an August back-to-school bump, and a heavy
  November–December run-up (December carries roughly 2.4× a baseline month).
* Product popularity follows a long-tail curve, with featured toys weighted
  about 2.2× — so a handful of SKUs carry a disproportionate share of revenue.
* Roughly 45% of customers are repeat buyers; about 4% of orders are cancelled.
* Order status is derived from age: older orders are `delivered`, recent ones
  `shipped` or `paid`.
* No order predates the account that placed it.

`scripts/seed.py` loads all of it into the database, so the admin dashboard has
a real year of orders to page through on first run.

Regenerate with a different shape:

```bash
python -m scripts.generate_synthetic_data --seed 7 --out ./data
python -m scripts.seed --reset          # then reload
```

---

## 11. Design notes

* **The browser is never trusted with money.** Cart lines are re-priced from
  the `products` table on every read; the checkout endpoint ignores any price
  in the request body; the Stripe session is built from the persisted order
  rows.
* **Stock moves once.** Checkout validates stock and creates a pending order.
  Only `mark_order_paid` — reached from the verified webhook, the dev-confirm
  endpoint, or an admin manually marking an order paid — decrements it, and it
  refuses to run twice on the same order.
* **Order lines are frozen.** `order_items` copies the name, slug, image and
  unit price at purchase time, so later catalogue edits never rewrite history.
  Products that appear on an order are deactivated rather than deleted.
* **Errors are typed.** Every failure — validation, auth, conflict — comes back
  as `{"error": {"code", "message", "field"}}`, which is what the frontend
  renders.
* **Guest carts.** Not signed in, the cart lives in `localStorage` and its
  totals are a preview only. On sign-in `POST /api/cart/merge` folds it into
  the server cart, skipping anything that no longer fits available stock.

---

## 12. Chatbot

A floating chat widget (`ChatWidget.tsx`, mounted in `Layout.tsx` and hidden on
`/admin` pages) lets shoppers ask questions about the store. It calls the
`POST /api/chat` endpoint, which requires a signed-in approved user (otherwise
`401 not_authenticated`), which forwards the message to a Lyzr agent through
`services/chat_service.py`. The Lyzr key stays on the server and is never sent to
the browser. Messages are limited to 500 characters, and each client is limited
to 20 requests per minute by an in-memory limiter. Logged-out visitors who click the
launcher see a popup (text in `frontend/src/components/chat/chatGate.ts`) saying
they must register and log in. The browser keeps a session id in `localStorage`
under `toybox.chat_session`, but it is cleared and the conversation wiped whenever
the signed-in user changes (including at page load), so it does not survive a
reload.

**Product cards.** After the Lyzr call, the endpoint looks for products named in
the reply (`services/chat_products.py`) and returns up to three of them as
`products` next to `reply`. Each card carries the slug, name, brand, category,
price in cents, an in-stock flag, the age range and the image URL; the stock
quantity is never sent. A product matches when its full name, or its name
without a trailing parenthetical such as "(100 pieces)", appears in the reply,
ignoring case and folding curly quotes and en/em dashes to plain ones. Only
whole-word matches count, so a name inside a longer word does not match. Names under 6 characters are ignored, the
longest match claims its text first, only active products count, cards follow
the order of first appearance, and out-of-stock products are included and
flagged. The lookup runs in a worker thread; if it fails, the failure is logged
and `products` is an empty list, so the shopper still gets the answer.

**Widget.** `ChatWidget.tsx` holds the state and layout. The parts live in
`frontend/src/components/chat/`: `ChatMessageBody` renders a reply, `ProductCard`
shows a product, `SuggestionChips` offers follow-up questions, and
`MessageActions` has copy and thumbs up/down. `chatText.ts` and
`chatSuggestions.ts` hold the pure logic. Replies show paragraphs, numbered
lists, bullet lists (`-`, `*`, `+`, `•`), `#` headings (shown as bold lines),
**bold** text, `inline code`, `---` rules (dropped), `[label](target)` links, and
bare URLs or site paths. A link appears only for an http(s) URL or one of the
site's own routes: an outside link shows its host next to the label, same-site
addresses show as the page path, anything else stays plain text, and nothing is
inserted as HTML. Suggestion chips are
deterministic: a starter list plus a topic table in `chatSuggestions.ts`, and the
knowledge base answers every suggested question. Thumbs are saved in this browser
only, under `toybox.chat_feedback`, and are never sent to the server. The "New
chat" button starts a new Lyzr session id. Escape closes the panel and focus
moves to the input when it opens. The chat text uses the Nunito font, applied only
through the `font-chat` class. Its Google Fonts stylesheet is requested from
fonts.googleapis.com only the first time a visitor opens the chat (injected by
`ChatWidget.tsx`); nothing is requested from Google on other page loads.

**Knowledge pack.** What the agent knows lives in `docs/chatbot-kb/`: eight
hand-written docs (`00`-`02` and `04`-`08`), a generated `products.md`, and `test-questions.md`,
a golden list of questions for checking the agent's answers. To refresh the
product data, run this from `backend/` and then re-upload the files to Lyzr,
chunking by heading:

```bash
python -m scripts.export_kb_products --base-url https://your-public-site
```

The committed `products.md` uses `localhost` links, so pass the public site URL
when exporting for a deployed store. `docs/chatbot-kb/_crawl/` is raw crawl
scratch and is not ingested.

**Lyzr upload set.** Upload docs `00` to `08` and `products.md`. Do not upload
`test-questions.md` (it is a checking list, not knowledge) or
`docs/chatbot-kb/_crawl/` (raw scratch that contains demo logins). Chunking by
heading drops the "prices and stock are a snapshot" note from product chunks, so
the agent's system prompt must carry it:

```text
You are the ToyBox store assistant. Answer shopper questions using only the attached knowledge base.
If the answer is not in the knowledge base, say you don't know and suggest the Feedback page on the site.
You cannot look up orders, change accounts, or process refunds. Prices and stock come from a snapshot and may have changed; say so when quoting them.
Keep replies short, friendly and plain text.
```

Lyzr's upload accepts only PDF, DOCX and TXT, so `docs/chatbot-kb/upload/` holds
`.txt` copies of the `docs/chatbot-kb/*.md` files for uploading. After editing a
`.md` doc, copy it over its `.txt` twin (PowerShell:
`Copy-Item docs\chatbot-kb\05-shipping-tax-pricing.md docs\chatbot-kb\upload\05-shipping-tax-pricing.txt`);
`products.txt` is `products.md` copied the same way.

**Feedback page dependency.** The knowledge pack (docs 00, 06, 07, 08) and the
agent prompt send shoppers to the Feedback page when the bot cannot help. The
`/feedback` route, the header link, `FeedbackPage.tsx` and
`VITE_N8N_FEEDBACK_FORM_URL` are not on this branch; they exist only in
uncommitted work. Land that work first or in the same merge, otherwise those
answers lead to the 404 page.

**Status.** The Lyzr request and response shape in `chat_service.py` (lines
tagged `# LYZR SHAPE`) was confirmed on 2026-10-04 against a live Lyzr agent:
the request matches the sample from the agent's API tab and the reply is read
from the `response` field. All 26 questions in
`docs/chatbot-kb/test-questions.md` were answered correctly, each in a fresh
session.

**Before deploying.**

* **Not implemented yet: the rate limiter's client IP.** Do not set
  `FORWARDED_ALLOW_IPS=*` (or `--forwarded-allow-ips='*'`). In the pinned uvicorn
  0.32.1, `*` makes the client IP the left-most `X-Forwarded-For` entry, which
  the client supplies. Unless Render's edge strips an incoming `X-Forwarded-For`,
  a caller can send a new value with every request, get a fresh limiter key each
  time, bypass the paid-API cap and grow the limiter's in-memory dict forever.
  Without trusting the proxy, all visitors share one key and one global cap of
  20 messages a minute. Before going public (recommended, not done), key the limiter on the user id now that chat is
  authenticated (a one-line change in `backend/app/routers/chat.py`), which also
  removes this spoofing concern. Otherwise key it on the right-most
  `X-Forwarded-For` entry (the hop the platform appended) with a small helper in
  `backend/app/routers/chat.py`, or set `forwarded-allow-ips` to the platform's
  actual proxy range. After deploying, send a forged `X-Forwarded-For` and check
  which key the limiter resolves. Also add a global per-minute and per-day
  ceiling or a Lyzr-side spend cap, evict empty limiter keys, and consider
  keying IPv6 clients by /64.
* The login page prints the seeded demo logins. That is fine locally, but remove
  it before any public deployment, and never put those credentials in the
  knowledge base.
* The whole site, including chat, assumes `localStorage` is available.
* Product cards come from the live database, so their prices and stock are
  current even when the answer text quotes the knowledge-base snapshot.
* The chat font is a third-party request, made only when a visitor first opens the
  chat. If Google is blocked or slow, the chat shows in the system sans-serif and
  still works.
