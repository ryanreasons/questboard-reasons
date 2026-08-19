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
