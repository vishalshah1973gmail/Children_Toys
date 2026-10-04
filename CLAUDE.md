# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

ToyBox — a full-stack e-commerce demo: React 18 + Vite + TypeScript frontend, FastAPI + SQLAlchemy 2.x + SQLite backend, Stripe Checkout (test mode) for payments, plus a separate one-request guest checkout path that never touches Stripe. See `README.md` for the full architecture diagram, database schema, API contract table, and design notes ("browser is never trusted with money", stock decrements exactly once, order lines are frozen snapshots) — read it before making payment or pricing changes.

## Commands

### Backend (run from `backend/`)
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic upgrade head                                 # apply migrations — required after pulling new model changes
python -m scripts.seed                               # catalogue + synthetic 2026 order history
uvicorn app.main:app --reload --port 8000
```
- `python -m scripts.seed --reset` — drop and recreate every table first
- `alembic revision --autogenerate -m "..."` — create a new migration after changing a model; always inspect the generated file before applying
- `pytest` or `python -m pytest -v` — run all tests; `pytest tests/test_checkout.py -v` for one file, `pytest tests/test_checkout.py::test_name -v` for one test. Each test gets its own throwaway SQLite file.

### Frontend (run from `frontend/`)
```bash
npm install
npm run dev         # http://localhost:5173
npm run build        # tsc -b && vite build
npm run typecheck    # tsc --noEmit, no build output
```
No lint script and no frontend test runner are configured.

### Both at once
- `.\scripts\start.ps1` / `.\scripts\stop.ps1` (Windows) — background uvicorn + vite, PID-tracked in `scripts/.pids/`, logs in `scripts/logs/`; polls `/health` until the backend responds before returning.
- `docker compose up --build` — same stack containerized; migrations run automatically on backend start; SQLite + uploads persist on named volumes.

### Stripe webhook testing
`stripe listen --forward-to localhost:8000/api/webhooks/stripe`, then copy the printed `whsec_...` into `backend/.env` as `STRIPE_WEBHOOK_SECRET` and restart uvicorn. Test card `4242 4242 4242 4242`. With `STRIPE_SECRET_KEY` blank and `ALLOW_DEV_PAYMENT=true`, checkout instead calls `POST /api/checkout/dev-confirm/{order_number}`, which runs the exact same confirmation path as the real webhook — use this for local iteration without any Stripe setup at all.

## Architecture

### Two independent checkout paths
1. **Authenticated checkout** (`routers/checkout.py: create_checkout_session`) — builds a *pending* order from the server-side cart, then either hands back a Stripe Checkout URL or, in dev mode, a synthetic confirm URL. The order is **not** marked paid here. Only the signature-verified webhook (`checkout.session.completed`) or `dev-confirm` calls `order_service.mark_order_paid`, which decrements stock and is idempotent — it refuses to run twice on the same order.
2. **Guest checkout** (`routers/checkout.py: guest_checkout`, `schemas/checkout_guest.py`) — one request, no auth, no Stripe: `order_service.create_guest_order` validates cart + card client-side-mirrored rules, creates the order already `PAID`, decrements stock immediately, and records a `Payment` with `provider="guest_form"`. Added in migration `0002_guest_checkout` (nullable `orders.user_id`, billing columns, card summary on `payments`) — if a guest-checkout request 500s, check `alembic current` vs `alembic heads` before anything else; the DB has been left mid-migration before.

### Money and pricing
All money is integer cents everywhere (frontend included — see `lib/format.ts` for the only place cents become a display string). `services/pricing.py: totals_for` is the single source of shipping/tax calculation; never trust a price or total sent from the browser — checkout re-reads `Product.price_cents` from the DB for every line.

### Email
`services/email_service.py` sends the guest-checkout receipt over real SMTP (Gmail + app password, configured via `SMTP_*` env vars) and is expected to fail without failing the order — `routers/checkout.py` catches the exception, logs it, and returns `email_sent: false`. Product images in that email are rendered via `_absolute_image_url`, which prefixes `settings.public_base_url` — a relative `image.url` (e.g. `/static/uploads/x.jpg`) is meaningless to an email client, since Gmail/Outlook fetch images from their own servers, not the recipient's browser. `PUBLIC_BASE_URL` must be a URL reachable from the public internet (not `localhost`) for images to actually load once deployed.

### Chatbot
A floating shopper chat widget (`frontend/src/components/ChatWidget.tsx`, mounted in `Layout.tsx`, hidden on `/admin` routes) talks to `POST /api/chat` (`routers/chat.py`), a public no-auth endpoint taking `{message, session_id}` and returning `{reply}`. The router calls `services/chat_service.py: ask_agent`, which proxies the message to a Lyzr agent over `httpx`; the Lyzr key (`LYZR_API_KEY`, plus `LYZR_AGENT_ID`) lives only in backend env and never reaches the browser. Messages are capped at 500 characters (`schemas/chat.py`), and an in-memory per-client rate limiter allows 20 requests per minute (`chat_rate_limit_per_minute`). Errors use the usual envelope: `chat_not_configured` (503, keys unset), `chat_unavailable` (503, Lyzr failed, timed out or returned a malformed reply), `rate_limited` (429), plus 422 for validation. The widget keeps its session id in `localStorage` under `toybox.chat_session`.

**Confirmed (2026-10-04):** the Lyzr request and response shape in `chat_service.py` (URL, `x-api-key` header, body fields, and reading the reply from `response`; the lines are tagged `# LYZR SHAPE`) matches the sample request from the real Lyzr account, and a live call through `POST /api/chat` returned a correct reply in the `response` field. All 26 questions in `docs/chatbot-kb/test-questions.md` were answered correctly when each was asked in a fresh session. If Lyzr changes its API, the tagged lines are the only place to edit.

The knowledge pack the agent is trained on is `docs/chatbot-kb/` (docs `00`-`08`, a generated `products.md`, and the `test-questions.md` golden list). To refresh product data, run `python -m scripts.export_kb_products [--base-url URL]` from `backend/` and re-upload the files to Lyzr, chunking by heading. The committed `products.md` has `localhost` links, so pass the public site URL as `--base-url` when exporting for a deployed site. `docs/chatbot-kb/_crawl/` is raw crawl scratch and is not ingested.

**Feedback page dependency:** the knowledge pack (docs 00, 06, 07, 08) and the agent prompt send shoppers to the Feedback page when the bot cannot help. The `/feedback` route, the header link, `FeedbackPage.tsx` and `VITE_N8N_FEEDBACK_FORM_URL` are not on this branch (they exist only in uncommitted work). Land that work first or in the same merge, otherwise those answers lead to the 404 page.

Before deploying (not implemented yet): do NOT set `FORWARDED_ALLOW_IPS=*` or `--forwarded-allow-ips='*'`. In the pinned uvicorn 0.32.1, `*` makes `request.client.host` the left-most `X-Forwarded-For` entry, which the client supplies, so unless Render's edge strips an incoming `X-Forwarded-For` a caller can send a fresh value on every request and get a new limiter key each time, bypassing the paid-API cap and growing the limiter's in-memory dict without bound. Without trusting the proxy, every visitor shares one key and one global 20-per-minute cap. Pre-deploy work: key the limiter on the right-most `X-Forwarded-For` entry (the hop the platform appended) through a small helper in `routers/chat.py`, or set `forwarded-allow-ips` to the platform's actual proxy range; after deploying, send a forged `X-Forwarded-For` and check the resolved key; add a global per-minute and per-day ceiling or a Lyzr-side spend cap; evict empty limiter keys and consider keying IPv6 clients by /64. Known limitation: the whole site, and therefore the chat call, needs `localStorage` to be available, because the shared axios request interceptor reads it unguarded. Security: the login page prints the seeded demo logins; that is for the local demo only, must be removed before any public deployment, and must never go into the chatbot knowledge base.

### Auth
JWT access token (30 min) + refresh token (7 days); the Axios interceptor in `api/client.ts` retries a 401 once after silently refreshing. Logout adds the refresh token's `jti` to a `revoked_tokens` denylist rather than trying to invalidate the JWT itself. `role` (`customer`/`admin`) gates every `/api/admin/*` route via `get_current_admin` in `core/deps.py`.

### Deployment (Render)
`render.yaml` at repo root is a Blueprint: backend deploys from `backend/Dockerfile` on Render's free web-service plan (sleeps after 15 min idle, auto-wakes on next request, URL is permanent regardless), with Postgres as a separate paid `databases:` entry (`toybox-db`, `plan: starter`) wired into `DATABASE_URL` via `fromDatabase` — free-tier Postgres is auto-deleted after 30 days, so this repo is set up assuming the paid DB tier for anything meant to persist. `db/session.py` is already dialect-agnostic (the SQLite `PRAGMA foreign_keys` listener checks the driver module name and no-ops on Postgres), so no code changes are needed to switch `DATABASE_URL` between `sqlite:///` and `postgresql://`. Secrets (`STRIPE_*`, `SMTP_*`, `LYZR_*`, `CORS_ORIGINS`, `PUBLIC_BASE_URL`) are marked `sync: false` in the Blueprint — set them in the Render dashboard, never in this file. The Dockerfile's `CMD` and `HEALTHCHECK` bind `${PORT:-8000}` because Render assigns its own port at runtime.
