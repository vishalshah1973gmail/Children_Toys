# Registration Approval Flow and Chat Gating — Design

Date: 2026-10-08
Status: approved in conversation, pending written-spec review

## Goal

Only validated people may use the site and chat. New registrations wait for admin approval. Chat requires a logged-in, approved user.

## Decisions (from the user)

- Admin notification goes to one address: `ADMIN_NOTIFY_EMAIL`, falling back to the first admin user's email.
- A pending or rejected user who logs in sees a specific message (after the password is verified).
- A rejected person may re-register with the same username/email; the account resets to pending and the admin is notified again.
- Existing and seeded users stay approved.
- Email failure never fails registration or an admin decision.

## Approach

Add `approval_status` to `users` (`pending` | `approved` | `rejected`). A separate registration-requests table was rejected: it needs a copy step on approval and duplicates uniqueness checks.

## 1. Data

- Migration `0003_user_approval` (down_revision `0002_guest_checkout`, uses `op.batch_alter_table` for SQLite) adds:
  - `approval_status` String(20), NOT NULL, `server_default='approved'`
  - `rejection_reason` String(500), nullable
  - `reviewed_at` DateTime, nullable
- Model default is `approved` so existing tests, fixtures and seed keep working. `/register` sets `pending` explicitly.
- `UserRead` gains `approval_status`.

## 2. Register

- `POST /api/auth/register` creates a `pending` user and returns `{status: "pending", message}`. No tokens, no auto-login.
- Duplicate username/email: 409 `already_registered` unless the existing row is `rejected`, in which case it is reset to `pending` with the new details and `rejection_reason`/`reviewed_at` cleared.
- Sends the admin notification email (try/except, logged).

## 3. Login and tokens

- `/login` verifies the password first, then:
  - `pending` → 403 `approval_pending` ("Your registration is awaiting admin approval.")
  - `rejected` → 403 `registration_rejected` (message includes the reason)
- `get_current_user` and `/refresh` reject non-approved users so old tokens stop working.

## 4. Admin API and email

- Routes under `/api/admin` (already admin-guarded):
  - `GET /registrations?status=pending`
  - `POST /registrations/{id}/approve`
  - `POST /registrations/{id}/reject` with required `reason` (5–500 chars)
- `/stats` gains `pending_approvals`.
- Decisions only act on `pending` rows; a repeat returns 409.
- `email_service` gains `send_mail(to, subject, html)` and three templates: admin notice, approved (with login link), rejected (with reason).
- New settings: `ADMIN_NOTIFY_EMAIL`, `FRONTEND_BASE_URL` (added to both `.env.example` files). `public_base_url` is the backend URL and is not reused.
- Order: commit the decision, then try the email. Responses include `email_sent`; the admin UI warns when false.

## 5. Frontend

- Register: on submit a modal says approval is in progress; OK goes to login. `authStore.register` stops storing tokens; `authApi.register` return type changes.
- Login: show the pending/rejected message by error code.
- Admin: new Approvals tab in `AdminLayout` with a pending-count badge; Overview shows a pending-approvals card linking to it. Approvals page lists name, email, username, date with Approve and Reject; Reject opens a modal with a required reason.
- Chat: `ChatWidget` reads the auth store. Logged out, either launcher opens a popup with the exact text below (Log in / Register links) and the panel stays closed. Session id is kept per user.
  > "I am sorry I cannot respond to you till you register and log in. This is necessary to ensure that only validated people are allowed to use the Application & Chat."
- `POST /api/chat` depends on `get_current_user` (401 when logged out), so the gate is enforced server-side too.

## 6. Tests and verification

- pytest: register returns pending with no tokens; login blocked for pending and rejected; approve unlocks login; reject requires reason; re-apply after rejection; repeat decision 409; chat 401 without token; email mocked, and email failure does not break the request.
- Update `test_auth.py::test_register_creates_customer_and_returns_tokens` and `test_chat.py` (add auth headers).
- Frontend: `npm run typecheck`; end-to-end browser run of the flow.

## Out of scope

Approve/reject via one-click email links, bulk actions, notification channels other than email.
