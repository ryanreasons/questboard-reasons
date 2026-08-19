# Milestone 3 Profile Boundary

Milestone 3 begins using the authenticated user-to-player link created in
Milestone 2 as a runtime access boundary.

## Runtime identity

`/auth/me` is the source of truth for both the authenticated account and its
linked Questboard hero. Child accounts are automatically bound to that linked
hero in the UI.

Parents retain the family administration experience. Children can still see
the family board, but only their linked hero is selectable for normal gameplay.
Parent-only controls such as Settings, Reset Week, Export, Import, focused
device switching, and the legacy admin PIN flow are not exposed to children.

The 4-digit admin PIN is only a convenience lock for an already authenticated
parent. It is not an authentication or authorization mechanism.

## Legacy API hardening in this slice

`GET /state`, `POST /state`, and `GET /config` require an authenticated session.
`POST /config` additionally requires the parent role.

`POST /state` remains a transitional whole-state compatibility endpoint so the
existing Questboard game can continue operating without a large rewrite. It is
authenticated, but it is not yet fine-grained per-action authorization.

For the current household deployment, the UI identity binding provides the
practical child boundary while preserving the existing game. A later hardening
slice can replace whole-state child mutation with explicit server-side action
endpoints if desired.
## Family account management

The parent Settings UI includes an Accounts tab backed by a parent-only
`GET /auth/accounts` endpoint. The endpoint returns public account metadata and
the linked Questboard hero; it never returns password hashes or session tokens.

From the Accounts tab, a signed-in parent can:

- view each login, role, active/disabled status, and linked hero;
- reset another family member's password;
- disable or re-enable another family member's account.

Password resets use the existing Argon2 password policy and revoke all sessions
for the target account. Disabling an account also revokes its active sessions.
The backend continues to prevent disabling the last active parent.

The currently signed-in parent is intentionally not reset or disabled from this
panel to avoid accidentally destroying the session being used to administer the
family. Another active parent can manage that account if needed.

Account deletion and Parent/Child role changes are intentionally deferred.
Disabling preserves player history and avoids introducing destructive identity
semantics before Gold ledger and historical-domain migrations are complete.
