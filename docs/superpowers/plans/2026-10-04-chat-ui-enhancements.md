# Chat Interface Enhancements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the ToyBox chat widget a polished Nunito-based design, formatted and clickable replies, suggestion chips, copy / new chat / thumbs tools, and live product cards for toys mentioned in answers.

**Architecture:** The backend finds product names in Lyzr's reply (server-side matching against the live database) and returns them as `products` next to `reply`. The widget is split into small components (message renderer, product card, chips, message actions); the pure text and suggestion logic lives in dependency-free `.ts` files that Node's built-in test runner can exercise directly.

**Tech Stack:** FastAPI, SQLAlchemy 2.x, pytest; React 18 + Vite + TypeScript + Tailwind; Node 24 built-in `node:test` for pure TS logic (no new packages).

**Spec:** `docs/superpowers/specs/2026-10-04-chat-ui-enhancements-design.md`

## Global Constraints

- No new packages and no changes to `package.json`, `requirements.txt` or lockfiles. Frontend pure-logic tests run with `node --test` (Node 24 strips TypeScript types natively); `frontend/tests/*.mjs` is outside `tsconfig`'s `include: ["src"]`.
- Pure files `frontend/src/components/chat/chatText.ts` and `chatSuggestions.ts` must have **no imports** and use only erasable TypeScript syntax (no enums, namespaces, parameter properties) so Node can run them as-is.
- Money is integer cents in the API; the widget formats it only with the existing `formatMoney` (`frontend/src/lib/format.ts`). Ages use `formatAgeRange`. Image paths go through `assetUrl` (`frontend/src/api/client.ts`).
- Nunito is chat-only: applied via a `font-chat` class on the chat root. Fonts load from Google Fonts; the system sans-serif is the fallback.
- Reply text is never inserted as HTML. Only `http(s)` URLs and the site's own routes become links; any other scheme stays plain text.
- `POST /api/chat` stays backward compatible: `products` is a new field defaulting to `[]`. A product-lookup failure must never cost the shopper their reply (log with `logger.exception`, return `products: []`).
- Code style: backend 4-space Python; frontend 2-space TS, ES modules, `async/await`, comments only for non-obvious WHY.
- Commits go on branch `chatbot-feature`, local only, never `git add -A`/`.`. The user's unrelated uncommitted files (`frontend/.env.example`, `frontend/src/App.tsx`, `frontend/src/components/Navbar.tsx`, `frontend/src/pages/FeedbackPage.tsx`) and untracked `docs/chatbot-kb/upload/` must stay unstaged and unmodified. Every commit ends with the trailer `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.
- Plan ruling: the spec's check "a thumbs choice survives a page reload" is reinterpreted. Conversations are not persisted (out of scope), so a stored vote has no message to re-attach to after a reload. Message ids therefore include a time component so stale votes can never attach to a new message, and the check becomes "the vote is stored under `toybox.chat_feedback`".

## Review Focus

1. A reply naming a product in a shortened form, a different case, or with a curly apostrophe must still produce its card; a reply naming no product (or only part of a word) must produce none. Pinned in Task 1.
2. A product-lookup failure must not cost the shopper the answer. Pinned in Task 2.
3. Hostile or odd reply text (HTML tags, `javascript:` links, unmatched `**`, a 5,000-character unbroken string, blank lines) must render safely. Pinned in Task 4's Node tests.
4. Blocked `localStorage` or an unavailable clipboard must not break chat. Handled by try/catch in Tasks 5 and 6; checked in the controller's browser pass.
5. Clicking a chip (or pressing Enter) while a reply is pending must not send twice, and a reply arriving after "New chat" must be discarded. Pinned by the `inFlight` ref and `chatGeneration` counter in Task 6; checked in the controller's browser pass.

---

## File Structure

| File | Responsibility |
|---|---|
| `backend/app/services/chat_products.py` (new) | `find_mentioned_products(db, reply)`: name matching. |
| `backend/tests/test_chat_products.py` (new) | Matching tests. |
| `backend/app/schemas/chat.py` (modify) | `ChatProduct`, `ChatResponse.products`. |
| `backend/app/routers/chat.py` (modify) | Attach cards; degrade gracefully. |
| `backend/tests/test_chat.py` (modify) | Endpoint tests for `products`. |
| `frontend/index.html`, `tailwind.config.js`, `src/index.css` (modify) | Nunito link, `font-chat`, animations. |
| `frontend/src/types.ts`, `src/api/chat.ts` (modify) | `ChatProduct`; `sendChatMessage` returns `{reply, products}`. |
| `frontend/src/components/chat/chatText.ts` (new) | Reply text → blocks/inline parts. |
| `frontend/tests/chatText.test.mjs` (new) | Node tests for the above. |
| `frontend/src/components/chat/ChatMessageBody.tsx` (new) | Renders parsed blocks. |
| `frontend/src/components/chat/chatSuggestions.ts` (new) | Starter list + follow-up topic table. |
| `frontend/tests/chatSuggestions.test.mjs` (new) | Node tests for suggestions. |
| `frontend/src/components/chat/ProductCard.tsx`, `SuggestionChips.tsx`, `MessageActions.tsx` (new) | One small component each. |
| `frontend/src/components/ChatWidget.tsx` (modify) | New shell wiring everything. |
| `CLAUDE.md`, `README.md` (modify) | Docs. |

---

### Task 1: Product-name matching service

**Files:**
- Create: `backend/app/services/chat_products.py`
- Test: `backend/tests/test_chat_products.py`

**Interfaces:**
- Consumes: `app.models.product.Product`; fixtures `db`, `product_factory` (`product_factory(slug, price_cents=1999, stock=10)` returns a committed Product whose `name` is derived from the slug, with category "Test Blocks", brand "Fixture Co", ages 36–96 months, one primary image).
- Produces: `MAX_PRODUCT_CARDS = 3` and `find_mentioned_products(db: Session, reply: str) -> list[Product]` (matched active products, ordered by first appearance, images and category eagerly loaded).

- [ ] **Step 1: Write the failing tests**

```python
"""Tests for matching product names inside chat replies."""

from app.services.chat_products import MAX_PRODUCT_CARDS, find_mentioned_products


def _product(db, product_factory, slug, name, **kwargs):
    product = product_factory(slug=slug, **kwargs)
    product.name = name
    db.commit()
    return product


def _ids(products):
    return [product.id for product in products]


def test_matches_full_name(db, product_factory):
    product = _product(db, product_factory, "rocket-race", "Rocket Race Family Board Game")
    found = find_mentioned_products(db, "Try the Rocket Race Family Board Game today!")
    assert _ids(found) == [product.id]


def test_matches_name_without_parenthetical(db, product_factory):
    product = _product(
        db, product_factory, "rainbow-rise", "Rainbow Rise Wooden Block Set (100 pieces)"
    )
    found = find_mentioned_products(db, "The Rainbow Rise Wooden Block Set is lovely.")
    assert _ids(found) == [product.id]


def test_matching_ignores_letter_case(db, product_factory):
    product = _product(db, product_factory, "rocket-race", "Rocket Race Family Board Game")
    found = find_mentioned_products(db, "ROCKET RACE FAMILY BOARD GAME is popular")
    assert _ids(found) == [product.id]


def test_curly_apostrophe_matches_straight(db, product_factory):
    product = _product(db, product_factory, "explorer-tent", "Explorer's Camping Tent Set")
    found = find_mentioned_products(db, "Take the Explorer’s Camping Tent Set outside.")
    assert _ids(found) == [product.id]


def test_caps_results_and_orders_by_first_appearance(db, product_factory):
    names = ["Alpha Puzzle Box", "Bravo Puzzle Box", "Charlie Puzzle Box", "Delta Puzzle Box"]
    products = {
        name.split()[0]: _product(db, product_factory, f"p-{index}", name)
        for index, name in enumerate(names)
    }
    reply = "Delta Puzzle Box, then Bravo Puzzle Box, Charlie Puzzle Box and Alpha Puzzle Box."
    found = find_mentioned_products(db, reply)
    assert len(found) == MAX_PRODUCT_CARDS == 3
    assert _ids(found) == [
        products["Delta"].id,
        products["Bravo"].id,
        products["Charlie"].id,
    ]


def test_same_product_named_twice_appears_once(db, product_factory):
    product = _product(db, product_factory, "castle-quest", "Castle Quest Brick Set")
    found = find_mentioned_products(
        db, "Castle Quest Brick Set is great. Again: Castle Quest Brick Set!"
    )
    assert _ids(found) == [product.id]


def test_longer_name_wins_over_contained_name(db, product_factory):
    plain = _product(db, product_factory, "marble-plain", "Marble Run Set")
    deluxe = _product(db, product_factory, "marble-deluxe", "Marble Run Set Deluxe")
    assert _ids(find_mentioned_products(db, "The Marble Run Set Deluxe is great")) == [deluxe.id]
    assert _ids(find_mentioned_products(db, "The Marble Run Set is great")) == [plain.id]


def test_partial_word_does_not_match(db, product_factory):
    _product(db, product_factory, "rocket-race", "Rocket Race Game")
    assert find_mentioned_products(db, "We stock Rocket Race Games too") == []


def test_inactive_product_excluded(db, product_factory):
    product = _product(db, product_factory, "retired", "Retired Wooden Train")
    product.is_active = False
    db.commit()
    assert find_mentioned_products(db, "The Retired Wooden Train is gone") == []


def test_out_of_stock_product_is_included(db, product_factory):
    product = _product(db, product_factory, "sold-out", "Sold Out Robot Kit", stock=0)
    found = find_mentioned_products(db, "The Sold Out Robot Kit is popular")
    assert _ids(found) == [product.id]


def test_no_match_returns_empty_list(db, product_factory):
    _product(db, product_factory, "rocket-race", "Rocket Race Family Board Game")
    assert find_mentioned_products(db, "Shipping is $5.99.") == []


def test_very_short_names_are_ignored(db, product_factory):
    _product(db, product_factory, "ball", "Ball")
    assert find_mentioned_products(db, "Ball") == []
```

- [ ] **Step 2: Run to verify failure**

Run (from `backend/`): `python -m pytest tests/test_chat_products.py -v`
Expected: FAIL with `ModuleNotFoundError: app.services.chat_products`.

- [ ] **Step 3: Write the implementation** `backend/app/services/chat_products.py`:

```python
"""Find ToyBox products mentioned in a chat reply so the widget can show live cards."""

from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.product import Product

MAX_PRODUCT_CARDS = 3
MIN_ALIAS_LENGTH = 6  # shorter names would match inside ordinary words

_PARENTHETICAL = re.compile(r"\s*\([^)]*\)\s*$")
_PUNCTUATION = str.maketrans(
    {"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-"}
)


def _normalise(text: str) -> str:
    return text.translate(_PUNCTUATION).lower()


def _aliases(name: str) -> set[str]:
    """The full name and the name without a trailing '(100 pieces)'-style note."""
    full = _normalise(name).strip()
    short = _PARENTHETICAL.sub("", full).strip()
    return {alias for alias in (full, short) if len(alias) >= MIN_ALIAS_LENGTH}


def find_mentioned_products(db: Session, reply: str) -> list[Product]:
    """Active products named in the reply, in order of first appearance (at most 3)."""
    haystack = _normalise(reply)
    rows = db.execute(select(Product.id, Product.name).where(Product.is_active.is_(True))).all()
    candidates = [(alias, product_id) for product_id, name in rows for alias in _aliases(name)]
    # Longest first, so "Marble Run Set Deluxe" claims its text before "Marble Run Set" can.
    candidates.sort(key=lambda item: len(item[0]), reverse=True)

    claimed: list[tuple[int, int]] = []
    first_seen: dict[int, int] = {}
    for alias, product_id in candidates:
        for match in re.finditer(rf"(?<!\w){re.escape(alias)}(?!\w)", haystack):
            start, end = match.span()
            if any(start < other_end and other_start < end for other_start, other_end in claimed):
                continue
            claimed.append((start, end))
            first_seen[product_id] = min(start, first_seen.get(product_id, start))

    ordered_ids = [
        product_id for product_id, _ in sorted(first_seen.items(), key=lambda item: item[1])
    ][:MAX_PRODUCT_CARDS]
    if not ordered_ids:
        return []

    products = db.scalars(
        select(Product)
        .where(Product.id.in_(ordered_ids))
        .options(selectinload(Product.images), selectinload(Product.category))
    ).all()
    by_id = {product.id: product for product in products}
    return [by_id[product_id] for product_id in ordered_ids]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_chat_products.py -v` then the full suite `python -m pytest -q`
Expected: 12 passed; full suite green and pristine.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/chat_products.py backend/tests/test_chat_products.py
git commit -m "feat: match product names in chat replies"
```

---

### Task 2: Chat response carries product cards

**Files:**
- Modify: `backend/app/schemas/chat.py`, `backend/app/routers/chat.py`
- Test: `backend/tests/test_chat.py`

**Interfaces:**
- Consumes: `chat_products.find_mentioned_products(db, reply) -> list[Product]` (Task 1); `app.db.session.get_db`; `Product.primary_image_url`, `Product.category.name`.
- Produces: `ChatProduct` schema `{slug, name, brand, category_name, price_cents, in_stock, min_age_months, max_age_months, image_url}` with classmethod `ChatProduct.from_product(product)`; `ChatResponse = {reply: str, products: list[ChatProduct] = []}`. `POST /api/chat` now returns `{"reply": ..., "products": [...]}`.

- [ ] **Step 1: Write the failing tests.** In `backend/tests/test_chat.py`, change `test_returns_agent_reply`'s final assertion to `assert response.json() == {"reply": "Shipping is $5.99.", "products": []}` and append:

```python
def test_reply_includes_product_cards(client, db, product_factory, monkeypatch):
    product = product_factory(slug="red-ball", price_cents=1999, stock=5)
    product.name = "Rocket Race Family Board Game"
    db.commit()

    async def fake(message, session_id):
        return "Try the Rocket Race Family Board Game, it is great."

    monkeypatch.setattr(chat_service, "ask_agent", fake)
    body = client.post("/api/chat", json=VALID).json()
    assert body["reply"].startswith("Try the Rocket Race")
    assert body["products"] == [
        {
            "slug": "red-ball",
            "name": "Rocket Race Family Board Game",
            "brand": "Fixture Co",
            "category_name": "Test Blocks",
            "price_cents": 1999,
            "in_stock": True,
            "min_age_months": 36,
            "max_age_months": 96,
            "image_url": "/static/uploads/red-ball.svg",
        }
    ]


def test_out_of_stock_card_is_flagged(client, db, product_factory, monkeypatch):
    product = product_factory(slug="sold-out", stock=0)
    product.name = "Sold Out Robot Kit"
    db.commit()

    async def fake(message, session_id):
        return "The Sold Out Robot Kit is popular."

    monkeypatch.setattr(chat_service, "ask_agent", fake)
    products = client.post("/api/chat", json=VALID).json()["products"]
    assert [item["in_stock"] for item in products] == [False]


def test_lookup_failure_still_returns_the_reply(client, monkeypatch, caplog):
    async def fake(message, session_id):
        return "Shipping is $5.99."

    def explode(db, reply):
        raise RuntimeError("database went away")

    monkeypatch.setattr(chat_service, "ask_agent", fake)
    monkeypatch.setattr("app.services.chat_products.find_mentioned_products", explode)
    with caplog.at_level("ERROR", logger="app.routers.chat"):
        response = client.post("/api/chat", json=VALID)
    assert response.status_code == 200
    assert response.json() == {"reply": "Shipping is $5.99.", "products": []}
    assert any(record.levelname == "ERROR" for record in caplog.records)
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_chat.py -v`
Expected: the new tests and the amended one FAIL (`products` missing from the response).

- [ ] **Step 3: Implement.** Replace `backend/app/schemas/chat.py`'s `ChatResponse` section so the file ends with:

```python
class ChatProduct(BaseModel):
    """A product mentioned in a reply, with live data for the widget's card."""

    slug: str
    name: str
    brand: str
    category_name: str
    price_cents: int
    in_stock: bool
    min_age_months: int
    max_age_months: int
    image_url: str | None = None

    @classmethod
    def from_product(cls, product: "Product") -> "ChatProduct":
        return cls(
            slug=product.slug,
            name=product.name,
            brand=product.brand,
            category_name=product.category.name,
            price_cents=product.price_cents,
            in_stock=product.stock_quantity > 0,
            min_age_months=product.min_age_months,
            max_age_months=product.max_age_months,
            image_url=product.primary_image_url,
        )


class ChatResponse(BaseModel):
    reply: str
    products: list[ChatProduct] = Field(default_factory=list)
```

and add to the top of that file `from typing import TYPE_CHECKING` plus

```python
if TYPE_CHECKING:  # pragma: no cover
    from app.models.product import Product
```

Replace `backend/app/routers/chat.py` with:

```python
"""Shopper chatbot endpoint. Public; no account required."""

import logging

from fastapi import APIRouter, Depends, Request
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import api_error
from app.db.session import get_db
from app.schemas.chat import ChatProduct, ChatRequest, ChatResponse
from app.services import chat_products, chat_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


def _cards_for(db: Session, reply: str) -> list[ChatProduct]:
    return [
        ChatProduct.from_product(product)
        for product in chat_products.find_mentioned_products(db, reply)
    ]


@router.post("", response_model=ChatResponse)
async def chat(
    payload: ChatRequest, request: Request, db: Session = Depends(get_db)
) -> ChatResponse:
    if not settings.lyzr_api_key or not settings.lyzr_agent_id:
        raise api_error(503, "chat_not_configured", "The chat assistant is not set up yet.")
    client_key = request.client.host if request.client else "unknown"
    if not chat_service.rate_limiter.allow(client_key):
        raise api_error(429, "rate_limited", "You're sending messages too quickly. Please wait a moment.")
    try:
        reply = await chat_service.ask_agent(payload.message, payload.session_id)
    except chat_service.ChatUnavailable:
        raise api_error(
            503,
            "chat_unavailable",
            "The assistant is having trouble right now. Please try again in a moment.",
        )
    # Cards are an extra: a failed lookup must never cost the shopper their answer.
    try:
        products = await run_in_threadpool(_cards_for, db, reply)
    except Exception:
        logger.exception("Product lookup for a chat reply failed")
        products = []
    return ChatResponse(reply=reply, products=products)
```

- [ ] **Step 4: Run tests**

Run: `python -m pytest tests/test_chat.py -v` then `python -m pytest -q`
Expected: all chat tests pass (the pre-existing ones unchanged except the one amended assertion); full suite green and pristine. If SQLite complains about threads, report it (the app engine already sets `check_same_thread=False`).

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/chat.py backend/app/routers/chat.py backend/tests/test_chat.py
git commit -m "feat: return product cards with chat replies"
```

---

### Task 3: Frontend foundation (font, animations, types, API)

**Files:**
- Modify: `frontend/index.html`, `frontend/tailwind.config.js`, `frontend/src/index.css`, `frontend/src/types.ts`, `frontend/src/api/chat.ts`, `frontend/src/components/ChatWidget.tsx` (one line)

**Interfaces:**
- Consumes: the Task 2 response shape.
- Produces: Tailwind class `font-chat`; CSS classes `chat-open`, `chat-dot`; type `ChatProduct` (same fields as the backend schema); `sendChatMessage(message, sessionId): Promise<ChatReply>` where `ChatReply = { reply: string; products: ChatProduct[] }`.

- [ ] **Step 1: Add the font link.** In `frontend/index.html`, inside `<head>` after the description meta, add:

```html
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link
      href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800&display=swap"
      rel="stylesheet"
    />
```

- [ ] **Step 2: Tailwind font.** In `frontend/tailwind.config.js` change `fontFamily` to:

```js
      fontFamily: {
        display: ['Georgia', 'Cambria', 'serif'],
        chat: ['Nunito', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
```

- [ ] **Step 3: Animations.** Append to the end of `frontend/src/index.css`:

```css
/* Chat widget motion. Both are switched off for people who prefer reduced motion. */
@keyframes chat-dot {
  0%, 80%, 100% { transform: translateY(0); opacity: 0.4; }
  40% { transform: translateY(-4px); opacity: 1; }
}
@keyframes chat-open {
  from { opacity: 0; transform: translateY(8px) scale(0.97); }
  to { opacity: 1; transform: none; }
}
.chat-dot { animation: chat-dot 1.2s infinite ease-in-out; }
.chat-dot:nth-child(2) { animation-delay: 0.15s; }
.chat-dot:nth-child(3) { animation-delay: 0.3s; }
.chat-open { animation: chat-open 0.18s ease-out; }
@media (prefers-reduced-motion: reduce) {
  .chat-dot, .chat-open { animation: none; }
}
```

- [ ] **Step 4: Types and API.** Append to `frontend/src/types.ts`:

```ts
export interface ChatProduct {
  slug: string
  name: string
  brand: string
  category_name: string
  price_cents: number
  in_stock: boolean
  min_age_months: number
  max_age_months: number
  image_url: string | null
}
```

Replace `frontend/src/api/chat.ts` with:

```ts
import type { ChatProduct } from '../types'
import { api } from './client'

export interface ChatReply {
  reply: string
  products: ChatProduct[]
}

export async function sendChatMessage(message: string, sessionId: string): Promise<ChatReply> {
  // Must exceed the backend's Lyzr timeout (45s) plus a possible Render cold start.
  const response = await api.post<{ reply: string; products?: ChatProduct[] }>(
    '/chat',
    { message, session_id: sessionId },
    { timeout: 60000 },
  )
  return { reply: response.data.reply, products: response.data.products ?? [] }
}
```

- [ ] **Step 5: Keep the current widget compiling.** In `frontend/src/components/ChatWidget.tsx` change

```tsx
      const reply = await sendChatMessage(text, sessionId.current)
```

to

```tsx
      const { reply } = await sendChatMessage(text, sessionId.current)
```

- [ ] **Step 6: Verify.** From `frontend/`: `npm run typecheck` then `npm run build`. Expected: both exit 0.

- [ ] **Step 7: Commit**

```bash
git add frontend/index.html frontend/tailwind.config.js frontend/src/index.css frontend/src/types.ts frontend/src/api/chat.ts frontend/src/components/ChatWidget.tsx
git commit -m "feat: chat font, motion styles and product-aware chat API client"
```

---

### Task 4: Reply formatter and renderer

**Files:**
- Create: `frontend/src/components/chat/chatText.ts`, `frontend/src/components/chat/ChatMessageBody.tsx`
- Test: `frontend/tests/chatText.test.mjs`

**Interfaces:**
- Consumes: `react-router-dom` `Link` (renderer only).
- Produces: `parseInline(line: string, siteOrigin: string): Inline[]`, `parseReply(text: string, siteOrigin: string): Block[]`, types `Inline`, `Block`; default export `ChatMessageBody({ text: string })`.

- [ ] **Step 1: Write the failing tests** `frontend/tests/chatText.test.mjs`:

```js
import assert from 'node:assert/strict'
import test from 'node:test'

import { parseInline, parseReply } from '../src/components/chat/chatText.ts'

const ORIGIN = 'http://localhost:5173'
const text = (value) => ({ kind: 'text', text: value })

test('plain text is one text part', () => {
  assert.deepEqual(parseInline('Shipping is $5.99.', ORIGIN), [text('Shipping is $5.99.')])
})

test('bold text becomes a bold part', () => {
  assert.deepEqual(parseInline('This is **important** news', ORIGIN), [
    text('This is '),
    { kind: 'bold', text: 'important' },
    text(' news'),
  ])
})

test('an unmatched ** stays plain text', () => {
  assert.deepEqual(parseInline('oops **not closed', ORIGIN), [text('oops **not closed')])
})

test('a localhost product URL becomes an in-app link and trailing punctuation stays text', () => {
  assert.deepEqual(
    parseInline('See http://localhost:5173/product/castle-quest-brick-set.', ORIGIN),
    [
      text('See '),
      {
        kind: 'link',
        text: 'http://localhost:5173/product/castle-quest-brick-set',
        href: '/product/castle-quest-brick-set',
        internal: true,
      },
      text('.'),
    ],
  )
})

test('a same-origin URL on another origin value is also in-app', () => {
  const parts = parseInline('Go to https://toybox.example/catalog?category=stem now', 'https://toybox.example')
  assert.deepEqual(parts[1], {
    kind: 'link',
    text: 'https://toybox.example/catalog?category=stem',
    href: '/catalog?category=stem',
    internal: true,
  })
})

test('a bare site path becomes an in-app link', () => {
  const parts = parseInline('Open /cart to continue', ORIGIN)
  assert.deepEqual(parts[1], { kind: 'link', text: '/cart', href: '/cart', internal: true })
})

test('a path that only starts like a route is not linked', () => {
  assert.deepEqual(parseInline('the /carton is here', ORIGIN), [text('the /carton is here')])
})

test('an external URL opens externally', () => {
  const parts = parseInline('Docs: https://example.com/page', ORIGIN)
  assert.deepEqual(parts[1], {
    kind: 'link',
    text: 'https://example.com/page',
    href: 'https://example.com/page',
    internal: false,
  })
})

test('a same-origin URL for a non-site route is external, not in-app', () => {
  const parts = parseInline('http://localhost:5173/admin', ORIGIN)
  assert.equal(parts[0].kind, 'link')
  assert.equal(parts[0].internal, false)
})

test('javascript: links stay plain text', () => {
  const input = '[click](javascript:alert(1))'
  assert.deepEqual(parseInline(input, ORIGIN), [text(input)])
})

test('HTML tags stay plain text', () => {
  const input = '<script>alert(1)</script><img src=x onerror=alert(1)>'
  assert.deepEqual(parseInline(input, ORIGIN), [text(input)])
})

test('a 5,000 character unbroken string parses without trouble', () => {
  const input = 'a'.repeat(5000)
  assert.deepEqual(parseInline(input, ORIGIN), [text(input)])
})

test('paragraphs are split on blank lines and keep single line breaks', () => {
  const blocks = parseReply('First line\nSecond line\n\nNext paragraph', ORIGIN)
  assert.equal(blocks.length, 2)
  assert.equal(blocks[0].kind, 'paragraph')
  assert.equal(blocks[0].lines.length, 2)
  assert.equal(blocks[1].kind, 'paragraph')
})

test('numbered lines become an ordered list', () => {
  const blocks = parseReply('Steps:\n1. Add toys\n2. Open the cart\n3) Pay', ORIGIN)
  assert.equal(blocks[0].kind, 'paragraph')
  assert.equal(blocks[1].kind, 'ordered')
  assert.equal(blocks[1].items.length, 3)
  assert.deepEqual(blocks[1].items[0], [text('Add toys')])
})

test('dash and bullet lines become a bullet list', () => {
  const blocks = parseReply('- one\n• two', ORIGIN)
  assert.equal(blocks.length, 1)
  assert.equal(blocks[0].kind, 'bullets')
  assert.equal(blocks[0].items.length, 2)
})

test('empty or whitespace input gives no blocks', () => {
  assert.deepEqual(parseReply('', ORIGIN), [])
  assert.deepEqual(parseReply('  \n \n', ORIGIN), [])
})
```

- [ ] **Step 2: Run to verify failure**

Run (from `frontend/`): `node --test tests/chatText.test.mjs`
Expected: FAIL (cannot find module `chatText.ts`).

- [ ] **Step 3: Write `frontend/src/components/chat/chatText.ts`:**

```ts
// Pure text -> structure helpers for chat replies. No imports and only erasable TypeScript
// syntax, so Node can run this file directly in tests.

export type Inline =
  | { kind: 'text'; text: string }
  | { kind: 'bold'; text: string }
  | { kind: 'link'; text: string; href: string; internal: boolean }

export type Block =
  | { kind: 'paragraph'; lines: Inline[][] }
  | { kind: 'ordered'; items: Inline[][] }
  | { kind: 'bullets'; items: Inline[][] }

// Product pages in older knowledge-base text use this address.
const LOCAL_DEV_ORIGIN = 'http://localhost:5173'
const SITE_ROUTE =
  'catalog(?:\\?[\\w=&%.-]*)?|cart|login|register|feedback|orders|account|checkout\\/guest|product\\/[a-z0-9-]+'
const SITE_PATH = new RegExp(`^\\/(?:${SITE_ROUTE})$`)
// No lookbehind (unsupported before Safari 16.4, where a bad regex would break the whole site
// at import time): a bare path must follow the start of the line, whitespace, a bracket or a quote.
// Groups: 1 bold text, 2 full URL, 3 character before a bare path, 4 bare path.
const INLINE_PATTERN = new RegExp(
  [
    '\\*\\*([^*\\n]+?)\\*\\*',
    '(https?:\\/\\/[^\\s<>()"\']+)',
    `(^|[\\s("'])(\\/(?:${SITE_ROUTE})(?![\\w/-]))`,
  ].join('|'),
  'g',
)
const TRAILING_PUNCTUATION = /[.,;:!?]+$/
const ORDERED_ITEM = /^\s*\d+[.)]\s+(.*)$/
const BULLET_ITEM = /^\s*[-•]\s+(.*)$/

function resolveLink(target: string, siteOrigin: string): { href: string; internal: boolean } | null {
  if (target.startsWith('/')) return SITE_PATH.test(target) ? { href: target, internal: true } : null
  let url: URL
  try {
    url = new URL(target)
  } catch {
    return null
  }
  if (url.protocol !== 'http:' && url.protocol !== 'https:') return null
  const path = url.pathname + url.search
  const sameSite = url.origin === siteOrigin || url.origin === LOCAL_DEV_ORIGIN
  if (sameSite && SITE_PATH.test(path)) return { href: path, internal: true }
  return { href: url.href, internal: false }
}

export function parseInline(line: string, siteOrigin: string): Inline[] {
  const parts: Inline[] = []
  let cursor = 0
  const pushText = (value: string) => {
    if (!value) return
    const last = parts[parts.length - 1]
    if (last && last.kind === 'text') last.text += value
    else parts.push({ kind: 'text', text: value })
  }
  for (const match of line.matchAll(INLINE_PATTERN)) {
    const index = match.index ?? 0
    pushText(line.slice(cursor, index))
    if (match[1] !== undefined) {
      parts.push({ kind: 'bold', text: match[1] })
    } else {
      // A bare path carries its preceding character in group 3; the link itself is group 4.
      if (match[4] !== undefined) pushText(match[3])
      const raw = match[4] ?? match[0]
      const linkText = raw.replace(TRAILING_PUNCTUATION, '')
      const link = resolveLink(linkText, siteOrigin)
      if (link) {
        parts.push({ kind: 'link', text: linkText, href: link.href, internal: link.internal })
        pushText(raw.slice(linkText.length))
      } else {
        pushText(raw)
      }
    }
    cursor = index + match[0].length
  }
  pushText(line.slice(cursor))
  return parts
}

export function parseReply(text: string, siteOrigin: string): Block[] {
  const blocks: Block[] = []
  let paragraph: Inline[][] = []
  const flushParagraph = () => {
    if (paragraph.length > 0) {
      blocks.push({ kind: 'paragraph', lines: paragraph })
      paragraph = []
    }
  }

  for (const rawLine of text.replace(/\r\n/g, '\n').split('\n')) {
    const line = rawLine.trimEnd()
    if (!line.trim()) {
      flushParagraph()
      continue
    }
    const ordered = ORDERED_ITEM.exec(line)
    if (ordered) {
      flushParagraph()
      const item = parseInline(ordered[1], siteOrigin)
      const last = blocks[blocks.length - 1]
      if (last && last.kind === 'ordered') last.items.push(item)
      else blocks.push({ kind: 'ordered', items: [item] })
      continue
    }
    const bullet = BULLET_ITEM.exec(line)
    if (bullet) {
      flushParagraph()
      const item = parseInline(bullet[1], siteOrigin)
      const last = blocks[blocks.length - 1]
      if (last && last.kind === 'bullets') last.items.push(item)
      else blocks.push({ kind: 'bullets', items: [item] })
      continue
    }
    paragraph.push(parseInline(line.trim(), siteOrigin))
  }
  flushParagraph()
  return blocks
}
```

- [ ] **Step 4: Run to verify the tests pass**

Run: `node --test tests/chatText.test.mjs`
Expected: all tests pass. If a regex detail in the tests disagrees with the implementation, fix the implementation to satisfy the stated behaviour (the test names are the contract); report any test you believe is wrong instead of weakening it silently.

- [ ] **Step 5: Write the renderer** `frontend/src/components/chat/ChatMessageBody.tsx`:

```tsx
import { Link } from 'react-router-dom'

import { type Inline, parseReply } from './chatText'

const LINK_CLASS =
  'font-semibold text-brand-700 underline decoration-brand-300 underline-offset-2 hover:text-brand-800'

function InlineParts({ parts }: { parts: Inline[] }) {
  return (
    <>
      {parts.map((part, index) => {
        if (part.kind === 'bold') {
          return (
            <strong key={index} className="font-bold">
              {part.text}
            </strong>
          )
        }
        if (part.kind === 'link') {
          return part.internal ? (
            <Link key={index} to={part.href} className={LINK_CLASS}>
              {part.text}
            </Link>
          ) : (
            <a key={index} href={part.href} target="_blank" rel="noopener noreferrer" className={LINK_CLASS}>
              {part.text}
            </a>
          )
        }
        return <span key={index}>{part.text}</span>
      })}
    </>
  )
}

/** Renders a bot reply. Text is always drawn as React text nodes, never as HTML. */
export default function ChatMessageBody({ text }: { text: string }) {
  const blocks = parseReply(text, window.location.origin)
  return (
    <div className="space-y-2 [overflow-wrap:anywhere]">
      {blocks.map((block, index) => {
        if (block.kind === 'ordered') {
          return (
            <ol key={index} className="list-decimal space-y-1 pl-5">
              {block.items.map((item, itemIndex) => (
                <li key={itemIndex}>
                  <InlineParts parts={item} />
                </li>
              ))}
            </ol>
          )
        }
        if (block.kind === 'bullets') {
          return (
            <ul key={index} className="list-disc space-y-1 pl-5">
              {block.items.map((item, itemIndex) => (
                <li key={itemIndex}>
                  <InlineParts parts={item} />
                </li>
              ))}
            </ul>
          )
        }
        return (
          <p key={index}>
            {block.lines.map((line, lineIndex) => (
              <span key={lineIndex}>
                {lineIndex > 0 && <br />}
                <InlineParts parts={line} />
              </span>
            ))}
          </p>
        )
      })}
    </div>
  )
}
```

- [ ] **Step 6: Verify.** From `frontend/`: `npm run typecheck` then `npm run build` (both exit 0) and `node --test tests/chatText.test.mjs` again.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/chat/chatText.ts frontend/src/components/chat/ChatMessageBody.tsx frontend/tests/chatText.test.mjs
git commit -m "feat: format chat replies safely (lists, bold, links)"
```

---

### Task 5: Suggestions, product card, message actions

**Files:**
- Create: `frontend/src/components/chat/chatSuggestions.ts`, `frontend/src/components/chat/ProductCard.tsx`, `frontend/src/components/chat/SuggestionChips.tsx`, `frontend/src/components/chat/MessageActions.tsx`
- Test: `frontend/tests/chatSuggestions.test.mjs`

**Interfaces:**
- Consumes: `ChatProduct` type, `formatMoney`, `formatAgeRange`, `assetUrl`.
- Produces: `STARTER_QUESTIONS: string[]` (4 items); `followUpQuestions(userQuestion: string, reply: string, asked: string[]): string[]` (always exactly 3, no repeats of `asked`, no duplicates); default exports `ProductCard({ product: ChatProduct })`, `SuggestionChips({ questions: string[]; onPick: (question: string) => void })`, `MessageActions({ id: string; text: string })`.

- [ ] **Step 1: Write the failing tests** `frontend/tests/chatSuggestions.test.mjs`:

```js
import assert from 'node:assert/strict'
import test from 'node:test'

import { STARTER_QUESTIONS, followUpQuestions } from '../src/components/chat/chatSuggestions.ts'

test('there are four starter questions', () => {
  assert.equal(STARTER_QUESTIONS.length, 4)
})

test('a shipping answer suggests tax and totals', () => {
  const result = followUpQuestions('How much is shipping?', 'Shipping is $5.99 under $50.', [
    'How much is shipping?',
  ])
  assert.equal(result.length, 3)
  assert.ok(result.includes('How much tax will I pay?'))
})

test('already asked questions are never suggested again', () => {
  const asked = ['How much tax will I pay?', 'What is the total for a $30.00 order?']
  const result = followUpQuestions('How much is shipping?', 'Shipping is $5.99.', asked)
  for (const question of asked) assert.ok(!result.includes(question))
})

test('unrelated text still gets three suggestions', () => {
  const result = followUpQuestions('zzz', 'qqq', [])
  assert.equal(result.length, 3)
})

test('suggestions have no duplicates', () => {
  const result = followUpQuestions('checkout card payment', 'guest checkout card cart', [])
  assert.equal(new Set(result).size, result.length)
})

test('matching is case-insensitive', () => {
  const upper = followUpQuestions('PASSWORD', 'SIGN IN WITH YOUR USERNAME', [])
  assert.ok(upper.includes('Can I sign in with my email address?'))
})
```

- [ ] **Step 2: Run to verify failure**

Run (from `frontend/`): `node --test tests/chatSuggestions.test.mjs`
Expected: FAIL (cannot find module `chatSuggestions.ts`).

- [ ] **Step 3: Write `frontend/src/components/chat/chatSuggestions.ts`:**

```ts
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
```

- [ ] **Step 4: Run to verify the tests pass**

Run: `node --test tests/chatSuggestions.test.mjs` — Expected: all pass.

- [ ] **Step 5: Write `frontend/src/components/chat/ProductCard.tsx`:**

```tsx
import { Link } from 'react-router-dom'

import { assetUrl } from '../../api/client'
import { formatAgeRange, formatMoney } from '../../lib/format'
import type { ChatProduct } from '../../types'

/** A product the assistant mentioned, with live price and stock from the database. */
export default function ProductCard({ product }: { product: ChatProduct }) {
  const image = assetUrl(product.image_url)
  return (
    <article className="flex gap-3 rounded-xl border border-ink-800/10 bg-white p-2.5 shadow-sm">
      {image ? (
        <img src={image} alt="" loading="lazy" className="h-16 w-16 shrink-0 rounded-lg object-cover" />
      ) : (
        <div aria-hidden="true" className="h-16 w-16 shrink-0 rounded-lg bg-orange-100" />
      )}
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-bold text-ink-900">{product.name}</p>
        <p className="truncate text-xs text-ink-700">
          {product.brand} · {formatAgeRange(product.min_age_months, product.max_age_months)}
        </p>
        <div className="mt-1.5 flex items-center justify-between gap-2">
          <p className="text-sm font-extrabold text-brand-700">
            {formatMoney(product.price_cents)}
            <span
              className={`ml-2 text-xs font-semibold ${product.in_stock ? 'text-emerald-700' : 'text-red-700'}`}
            >
              {product.in_stock ? 'In stock' : 'Out of stock'}
            </span>
          </p>
          <Link
            to={`/product/${product.slug}`}
            aria-label={`View ${product.name}`}
            className="shrink-0 rounded-full bg-brand-600 px-3 py-1 text-xs font-bold text-white hover:bg-brand-700"
          >
            View
          </Link>
        </div>
      </div>
    </article>
  )
}
```

- [ ] **Step 6: Write `frontend/src/components/chat/SuggestionChips.tsx`:**

```tsx
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
```

- [ ] **Step 7: Write `frontend/src/components/chat/MessageActions.tsx`:**

```tsx
import { useEffect, useState } from 'react'

const FEEDBACK_KEY = 'toybox.chat_feedback'
type Vote = 'up' | 'down'

function readVotes(): Record<string, Vote> {
  try {
    const raw = localStorage.getItem(FEEDBACK_KEY)
    return raw ? (JSON.parse(raw) as Record<string, Vote>) : {}
  } catch {
    return {}
  }
}

function writeVote(id: string, vote: Vote | null) {
  try {
    const votes = readVotes()
    if (vote) votes[id] = vote
    else delete votes[id]
    localStorage.setItem(FEEDBACK_KEY, JSON.stringify(votes))
  } catch {
    // Storage blocked: the choice is simply not remembered.
  }
}

const ICON = {
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 2,
  strokeLinecap: 'round' as const,
  strokeLinejoin: 'round' as const,
  'aria-hidden': true,
  className: 'h-4 w-4',
}

const BUTTON =
  'grid h-7 w-7 place-items-center rounded-full text-ink-700 hover:bg-orange-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-500'

/** Copy and thumbs up/down for one bot reply. Votes live in this browser only. */
export default function MessageActions({ id, text }: { id: string; text: string }) {
  const [copied, setCopied] = useState(false)
  const [vote, setVote] = useState<Vote | null>(null)

  useEffect(() => {
    if (!copied) return
    const timer = window.setTimeout(() => setCopied(false), 1500)
    return () => window.clearTimeout(timer)
  }, [copied])

  async function copy() {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
    } catch {
      // Clipboard unavailable: nothing to show.
    }
  }

  function choose(next: Vote) {
    const value = vote === next ? null : next
    setVote(value)
    writeVote(id, value)
  }

  return (
    <div className="flex items-center gap-1">
      <button type="button" onClick={copy} className={BUTTON} aria-label="Copy answer" title="Copy answer">
        {copied ? (
          <svg {...ICON}>
            <polyline points="20 6 9 17 4 12" />
          </svg>
        ) : (
          <svg {...ICON}>
            <rect x="9" y="9" width="11" height="11" rx="2" />
            <path d="M5 15V6a2 2 0 0 1 2-2h9" />
          </svg>
        )}
      </button>
      {copied && (
        <span role="status" className="text-xs font-semibold text-emerald-700">
          Copied
        </span>
      )}
      <button
        type="button"
        onClick={() => choose('up')}
        aria-pressed={vote === 'up'}
        className={`${BUTTON} ${vote === 'up' ? 'bg-orange-100 text-brand-700' : ''}`}
        aria-label="Helpful"
        title="Helpful"
      >
        <svg {...ICON}>
          <path d="M7 10v10H3V10zM7 10l4-7a2 2 0 0 1 2 2v4h6a2 2 0 0 1 2 2l-1.5 7a2 2 0 0 1-2 1.5H7" />
        </svg>
      </button>
      <button
        type="button"
        onClick={() => choose('down')}
        aria-pressed={vote === 'down'}
        className={`${BUTTON} ${vote === 'down' ? 'bg-orange-100 text-brand-700' : ''}`}
        aria-label="Not helpful"
        title="Not helpful"
      >
        <svg {...ICON}>
          <path d="M17 14V4h4v10zM17 14l-4 7a2 2 0 0 1-2-2v-4H5a2 2 0 0 1-2-2l1.5-7A2 2 0 0 1 6.5 4H17" />
        </svg>
      </button>
    </div>
  )
}
```

- [ ] **Step 8: Verify.** From `frontend/`: `npm run typecheck`, `npm run build` (exit 0) and `node --test` (all pass).

- [ ] **Step 9: Commit**

```bash
git add frontend/src/components/chat/chatSuggestions.ts frontend/src/components/chat/ProductCard.tsx frontend/src/components/chat/SuggestionChips.tsx frontend/src/components/chat/MessageActions.tsx frontend/tests/chatSuggestions.test.mjs
git commit -m "feat: chat suggestions, product card and message actions"
```

---

### Task 6: Chat widget redesign

**Files:**
- Modify (full rewrite): `frontend/src/components/ChatWidget.tsx`

**Interfaces:**
- Consumes: `sendChatMessage` → `ChatReply`; `ChatMessageBody`, `ProductCard`, `SuggestionChips`, `MessageActions`; `STARTER_QUESTIONS`, `followUpQuestions`; classes `font-chat`, `chat-open`, `chat-dot`.
- Produces: default export `ChatWidget()` (no props, unchanged mount in `Layout.tsx`).

- [ ] **Step 1: Replace `frontend/src/components/ChatWidget.tsx` with:**

```tsx
import { FormEvent, useEffect, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'

import { sendChatMessage } from '../api/chat'
import { toApiError } from '../api/client'
import type { ChatProduct } from '../types'
import ChatMessageBody from './chat/ChatMessageBody'
import MessageActions from './chat/MessageActions'
import ProductCard from './chat/ProductCard'
import SuggestionChips from './chat/SuggestionChips'
import { STARTER_QUESTIONS, followUpQuestions } from './chat/chatSuggestions'

type ChatMessage = {
  id: string
  role: 'user' | 'bot'
  text: string
  time: number
  products?: ChatProduct[]
  suggestions?: string[]
}

const SESSION_KEY = 'toybox.chat_session'
const MAX_CHARS = 500
const GREETING = "Hi! I'm the ToyBox assistant. Ask me about products, checkout, shipping or tax."

function greeting(): ChatMessage {
  return { id: 'greeting', role: 'bot', text: GREETING, time: Date.now() }
}

// Both forms match the backend pattern ^[A-Za-z0-9_-]{8,64}$.
function newSessionId(): string {
  return crypto.randomUUID?.() ?? `s${Date.now()}${Math.random().toString(36).slice(2)}`
}

function startNewSession(): string {
  const created = newSessionId()
  try {
    localStorage.setItem(SESSION_KEY, created)
  } catch {
    // Storage blocked: the id lives in memory for this page only.
  }
  return created
}

/** Falls back to an in-memory id when localStorage is blocked. */
function loadSessionId(): string {
  try {
    const existing = localStorage.getItem(SESSION_KEY)
    if (existing) return existing
  } catch {
    return newSessionId()
  }
  return startNewSession()
}

function formatTime(time: number): string {
  return new Date(time).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })
}

function Avatar({ size }: { size: 'sm' | 'md' }) {
  const box = size === 'md' ? 'h-10 w-10' : 'h-7 w-7'
  const icon = size === 'md' ? 'h-6 w-6' : 'h-4 w-4'
  return (
    <span
      aria-hidden="true"
      className={`grid shrink-0 place-items-center rounded-full bg-white text-brand-600 shadow-sm ${box}`}
    >
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
        className={icon}
      >
        <rect x="4" y="7" width="16" height="12" rx="3" />
        <path d="M12 7V4" />
        <circle cx="12" cy="3.5" r="1" />
        <circle cx="9" cy="13" r="1" fill="currentColor" />
        <circle cx="15" cy="13" r="1" fill="currentColor" />
        <path d="M9.5 16.5c1.5 1 3.5 1 5 0" />
      </svg>
    </span>
  )
}

export default function ChatWidget() {
  const location = useLocation()
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<ChatMessage[]>(() => [greeting()])
  const [draft, setDraft] = useState('')
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const sessionId = useRef<string | null>(null)
  const inFlight = useRef(false)
  const chatGeneration = useRef(0)
  const idCounter = useRef(0)
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const launcherRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    bottomRef.current?.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'end' })
  }, [messages, pending, open])

  useEffect(() => {
    if (open) inputRef.current?.focus()
  }, [open])

  // Hooks above must all run before this early return.
  if (location.pathname.startsWith('/admin')) return null

  // The time part keeps ids unique across page loads, so a stored vote can never attach to a new message.
  const makeId = () => `${Date.now().toString(36)}-${idCounter.current++}`

  async function sendText(raw: string) {
    const text = raw.trim()
    if (!text || inFlight.current) return
    // Generated once, lazily, so it is not recomputed on every render.
    if (sessionId.current === null) sessionId.current = loadSessionId()
    const generation = chatGeneration.current
    const asked = [...messages.filter((message) => message.role === 'user').map((m) => m.text), text]
    inFlight.current = true
    setDraft('')
    setError(null)
    setMessages((current) => [...current, { id: makeId(), role: 'user', text, time: Date.now() }])
    setPending(true)
    try {
      const { reply, products } = await sendChatMessage(text, sessionId.current)
      // "New chat" was pressed while waiting: this reply belongs to the old conversation.
      if (generation !== chatGeneration.current) return
      setMessages((current) => [
        ...current,
        {
          id: makeId(),
          role: 'bot',
          text: reply,
          time: Date.now(),
          products,
          suggestions: followUpQuestions(text, reply, asked),
        },
      ])
    } catch (caught) {
      if (generation === chatGeneration.current) setError(toApiError(caught).message)
    } finally {
      if (generation === chatGeneration.current) {
        inFlight.current = false
        setPending(false)
      }
    }
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    void sendText(draft)
  }

  function newChat() {
    chatGeneration.current += 1
    inFlight.current = false
    sessionId.current = startNewSession()
    setMessages([greeting()])
    setDraft('')
    setError(null)
    setPending(false)
    inputRef.current?.focus()
  }

  const hasUserMessage = messages.some((message) => message.role === 'user')
  const lastMessage = messages[messages.length - 1]

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col items-end gap-3 font-chat">
      {open && (
        <section
          aria-label="ToyBox assistant"
          onKeyDown={(event) => {
            if (event.key === 'Escape') {
              setOpen(false)
              launcherRef.current?.focus()
            }
          }}
          className="chat-open flex h-[min(36rem,calc(100dvh-6rem))] w-[22rem] max-w-[calc(100vw-2rem)] flex-col overflow-hidden rounded-2xl border border-ink-800/10 bg-[#fffaf5] shadow-2xl"
        >
          <header className="flex items-center gap-3 bg-gradient-to-r from-brand-600 to-brand-700 px-4 py-3 text-white">
            <Avatar size="md" />
            <div className="min-w-0 flex-1">
              <p className="text-base font-extrabold leading-tight">ToyBox assistant</p>
              <p className="flex items-center gap-1.5 text-xs text-white/90">
                <span aria-hidden="true" className="h-2 w-2 rounded-full bg-emerald-300" />
                Here to help
              </p>
            </div>
            <button
              type="button"
              onClick={newChat}
              aria-label="Start a new chat"
              title="Start a new chat"
              className="grid h-9 w-9 place-items-center rounded-full hover:bg-white/15 focus-visible:outline focus-visible:outline-2 focus-visible:outline-white"
            >
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth={2}
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
                className="h-5 w-5"
              >
                <path d="M3 12a9 9 0 0 1 15.5-6.2L21 8" />
                <path d="M21 3v5h-5" />
                <path d="M21 12a9 9 0 0 1-15.5 6.2L3 16" />
                <path d="M3 21v-5h5" />
              </svg>
            </button>
          </header>

          <div className="flex-1 space-y-4 overflow-y-auto px-3 py-4 text-[15px] leading-relaxed" aria-live="polite">
            {messages.map((message, index) => {
              const isLast = message === lastMessage
              if (message.role === 'user') {
                return (
                  <div key={message.id} className="flex flex-col items-end">
                    <p className="max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-br-md bg-brand-600 px-3.5 py-2.5 text-white [overflow-wrap:anywhere]">
                      {message.text}
                    </p>
                    <span className="mt-1 text-[11px] text-ink-700/70">{formatTime(message.time)}</span>
                  </div>
                )
              }
              const showAvatar = messages[index + 1]?.role !== 'bot'
              return (
                <div key={message.id} className="flex items-end gap-2">
                  {showAvatar ? <Avatar size="sm" /> : <span className="w-7 shrink-0" />}
                  <div className="min-w-0 max-w-[85%] flex-1 space-y-2">
                    <div className="rounded-2xl rounded-bl-md border border-ink-800/10 bg-white px-3.5 py-2.5 text-ink-800 shadow-sm">
                      <ChatMessageBody text={message.text} />
                    </div>
                    {message.products && message.products.length > 0 && (
                      <div className="space-y-2">
                        {message.products.map((product) => (
                          <ProductCard key={product.slug} product={product} />
                        ))}
                      </div>
                    )}
                    <div className="flex items-center justify-between">
                      <span className="text-[11px] text-ink-700/70">{formatTime(message.time)}</span>
                      {message.id !== 'greeting' && <MessageActions id={message.id} text={message.text} />}
                    </div>
                    {isLast && !pending && !hasUserMessage && (
                      <SuggestionChips questions={STARTER_QUESTIONS} onPick={(q) => void sendText(q)} />
                    )}
                    {isLast && !pending && message.suggestions && (
                      <SuggestionChips questions={message.suggestions} onPick={(q) => void sendText(q)} />
                    )}
                  </div>
                </div>
              )
            })}

            {pending && (
              <div className="flex items-end gap-2">
                <Avatar size="sm" />
                <div
                  role="status"
                  aria-label="The assistant is typing"
                  className="flex items-center gap-1.5 rounded-2xl rounded-bl-md border border-ink-800/10 bg-white px-4 py-3 shadow-sm"
                >
                  <span className="chat-dot inline-block h-2 w-2 rounded-full bg-ink-700/60" />
                  <span className="chat-dot inline-block h-2 w-2 rounded-full bg-ink-700/60" />
                  <span className="chat-dot inline-block h-2 w-2 rounded-full bg-ink-700/60" />
                </div>
              </div>
            )}
            {error && (
              <p role="alert" className="rounded-xl bg-red-50 px-3 py-2 text-sm text-red-700">
                {error}
              </p>
            )}
            <div ref={bottomRef} />
          </div>

          <form onSubmit={handleSubmit} className="flex items-center gap-2 border-t border-ink-800/10 bg-white p-3">
            <input
              ref={inputRef}
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              maxLength={MAX_CHARS}
              placeholder="Ask a question…"
              aria-label="Your question"
              className="min-w-0 flex-1 rounded-full border border-ink-800/15 bg-orange-50/50 px-4 py-2.5 text-[15px] outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/30"
            />
            <button
              type="submit"
              disabled={pending || !draft.trim()}
              aria-label="Send message"
              className="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-brand-600 text-white hover:bg-brand-700 disabled:opacity-40"
            >
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth={2}
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
                className="h-5 w-5"
              >
                <line x1="5" y1="12" x2="19" y2="12" />
                <polyline points="12 5 19 12 12 19" />
              </svg>
            </button>
          </form>
        </section>
      )}
      <button
        ref={launcherRef}
        type="button"
        onClick={() => setOpen((current) => !current)}
        aria-expanded={open}
        aria-label={open ? 'Close chat' : 'Open chat'}
        title={open ? 'Close chat' : 'Chat with us'}
        className="h-14 w-14 rounded-full bg-brand-600 hover:bg-brand-700 text-white shadow-lg grid place-items-center focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2 focus:outline-none"
      >
        {open ? (
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
            className="h-6 w-6"
          >
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        ) : (
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
            className="h-6 w-6"
          >
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
        )}
      </button>
    </div>
  )
}
```

- [ ] **Step 2: Verify.** From `frontend/`: `npm run typecheck`, `npm run build` (both exit 0), `node --test` (all pass).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ChatWidget.tsx
git commit -m "feat: redesign chat widget with avatar, chips, cards and reply tools"
```

(The controller then runs the browser pass described in the spec's Testing section; fixes found there go through the normal review/fix loop.)

---

### Task 7: Documentation

**Files:**
- Modify: `CLAUDE.md`, `README.md`

**Interfaces:**
- Consumes: the final behaviour of Tasks 1–6 (verify each fact in code before writing it).
- Produces: updated docs.

- [ ] **Step 1:** In `CLAUDE.md`'s `### Chatbot` subsection add (compact, same style): the `POST /api/chat` response is now `{reply, products}`; `services/chat_products.py` matches product names in the reply (full name or name without a trailing parenthetical, case/curly-quote insensitive, names under 6 characters ignored, longest match wins, at most 3, active products only, ordered by first appearance); a lookup failure is logged and returns `products: []`; the widget is split into `ChatWidget.tsx` plus `components/chat/` (message renderer, product card, chips, message actions, pure `chatText.ts` and `chatSuggestions.ts`); Nunito loads from Google Fonts for the chat only; pure frontend logic is tested with `node --test` from `frontend/` (Node 24, no packages); thumbs are stored in the browser only (`toybox.chat_feedback`); chips are deterministic, from `chatSuggestions.ts`.
- [ ] **Step 2:** In `README.md` update section 13 ("Chatbot") the same way, update the `POST /chat` row in the API table to mention `products`, add the new files to the file tree, and add `node --test` (run from `frontend/`) to the section on running tests.
- [ ] **Step 3:** Run `python -m pytest -q` (backend), `npm run typecheck` and `node --test` from `frontend/` (frontend). Expected: all green.
- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md README.md
git commit -m "docs: document chat product cards, new widget structure and node tests"
```

---

## Self-Review

- **Spec coverage:** font + animations (Task 3), polish/avatar/header/typing/timestamps/focus/Escape (Task 6), formatting + links (Task 4), chips (Task 5, wired in Task 6), copy / thumbs / new chat (Tasks 5 and 6), product cards backend (Tasks 1–2) and frontend (Tasks 5–6), docs (Task 7), failure behaviour (Task 2), testing (pytest, node tests, controller browser pass). No gaps found.
- **Placeholders:** none; every code step is complete.
- **Type consistency:** `ChatProduct` fields match between `schemas/chat.py` and `types.ts` (`slug, name, brand, category_name, price_cents, in_stock, min_age_months, max_age_months, image_url`); `sendChatMessage` → `ChatReply {reply, products}` consumed in Task 6; `followUpQuestions(userQuestion, reply, asked)` matches its call; `MessageActions({id, text})` and `ProductCard({product})` match their uses; `parseReply(text, siteOrigin)` matches `ChatMessageBody`.
- **Known deviation recorded:** thumbs "survive reload" reinterpreted (see Global Constraints).
