# Copilot instructions for Questboard derivative

## Non-negotiable rules
- Preserve the existing QuestBoard RPG identity unless a change is explicitly requested.
- Keep Gold as the only spendable currency.
- Do not introduce secondary currencies for spending.
- Treat XP, Merit, Royal Standing, inventory items, and resources as non-currency systems.
- Protect append-only ledger integrity: no in-place edits or deletes of ledger rows.
- Use compensating transactions for corrections.
- Require server-side authorization for all sensitive actions.
- Do not rely on client-side PINs or UI gating as the security boundary.
- Preserve upstream license text and attribution.

## Engineering approach
- Prefer incremental changes over broad refactors.
- Add or alter schema through migrations.
- Keep persistence durable and structured.
- Make state transitions explicit and auditable.
- Keep RPG math separate from household finance math.
- Never multiply real Job wages with RPG bonuses.

## Implementation expectations
- Add tests for authentication, authorization, financial movement, and permission-sensitive workflows.
- Explain any architectural change that affects persistence, identity, accounting, or authorization.
- Keep changes narrowly scoped to the requested feature.
- Preserve existing gameplay unless a later milestone explicitly changes it.

## Feature boundaries
- Do not create a second spendable currency.
- Do not implement unapproved child-to-child Gold trading.
- Do not hard-code punishment policies unless the product explicitly defines them.
- Do not replace React or FastAPI for stylistic reasons.
- Do not remove existing RPG systems such as combat, dungeon play, streaks, power-ups, history, or rewards.
