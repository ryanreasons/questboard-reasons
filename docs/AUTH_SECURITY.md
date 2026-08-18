# Authentication Security

Milestone 2 introduces real server-verified family accounts without replacing the legacy whole-state gameplay API yet.

## Passwords

- Passwords are normalized with Unicode NFC before hashing or verification.
- Passwords must be at least 15 Unicode code points for creation/reset and are capped at 256 code points.
- Passwords may contain spaces and are not subject to composition rules.
- Passwords are hashed with Argon2 through `pwdlib`; plaintext passwords are never persisted.
- Login failures use the same generic `invalid credentials` response for unknown usernames and bad passwords. Unknown usernames still perform an Argon2 verification against a dummy hash.

## Usernames and roles

- Usernames are NFC-normalized, trimmed, and case-folded before storage and lookup.
- Supported roles in this milestone are `parent` and `child`.
- Parent-only operations are enforced by FastAPI dependencies on the server.
- A normal API request cannot disable the last active parent account.

## Sessions

- Browser sessions use cryptographically random opaque tokens generated with Python `secrets`.
- Only SHA-256 hashes of session tokens are stored in SQLite.
- The raw token is stored only in an HttpOnly cookie named `qb_session`.
- Cookie `SameSite` is `Lax`, path is `/`, and `Secure` is controlled by `QUESTBOARD_SECURE_COOKIES`.
- Session lifetime is controlled by `QUESTBOARD_SESSION_HOURS` and defaults to 168 hours (7 days).
- Logout revokes the current server-side session.
- Disabling a user or resetting that user's password revokes all existing sessions for that user.
- Expired, revoked, or disabled-user sessions cannot authorize requests.

## Initial bootstrap

`POST /auth/bootstrap` works only while the `users` table is empty. Bootstrap acquires a SQLite `BEGIN IMMEDIATE` transaction before checking and inserting, so competing initial-parent requests cannot both succeed.

## Transitional limitation

Legacy `/state` and `/config` endpoints remain operational for compatibility. Current QuestBoard gameplay still performs client-side mutations and persists whole JSON blobs, so those legacy writes are not yet treated as fine-grained authorized actions. New authentication/account-management APIs are server-authorized; later milestones must move sensitive gameplay mutations behind explicit server-side actions before the legacy state boundary can be considered secure.
