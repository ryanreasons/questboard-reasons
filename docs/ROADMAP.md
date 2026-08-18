# Questboard Derivative Roadmap

## Milestone 1: Persistence foundation
**Goal:** replace the fragile JSON-blob model with durable structured storage.

**Scope**
- Add SQLite-backed persistence.
- Define schema for accounts, profiles, sessions, settings, state snapshots, and append-only ledgers.
- Introduce migrations and seed/opening-balance support.

**Dependencies**
- None.

**Acceptance criteria**
- Current gameplay state can be saved and restored from structured storage.
- Ledger tables support immutable transactions.
- Existing gameplay data can be migrated without changing gameplay behavior.

## Milestone 2: Authentication and authorization
**Goal:** ensure every action is tied to a real account and server-side permissions.

**Scope**
- Password-based login.
- Parent/admin roles.
- Server-side authorization for state-changing actions.
- Session handling for logged-in users.

**Dependencies**
- Requires Milestone 1 storage foundation.

**Acceptance criteria**
- Users can only act as themselves unless they have parent/admin privileges.
- Client-side gating is no longer the authority for sensitive actions.

## Milestone 3: Profiles and account views
**Goal:** expose durable per-person views without mutating core gameplay.

**Scope**
- Profile records and read-only viewing of other members.
- Profile sections for Gold, class, level, inventory, rewards, history, Merit, Royal Standing, and goals.

**Dependencies**
- Milestones 1-2.

**Acceptance criteria**
- Each person has a stable profile identity.
- Existing RPG data remains visible.

## Milestone 4: Gold ledger and Kingdom Vault
**Goal:** make all Gold movement auditable.

**Scope**
- Immutable Gold ledger.
- Wallet/balance derivation from transactions.
- Vault tracking for deductions and other non-user holdings.

**Dependencies**
- Milestone 1.

**Acceptance criteria**
- All Gold-changing actions create ledger entries.
- Corrections are additive, not destructive.
- Vault balance and per-player contribution are visible.

## Milestone 5: Royal Mail and approvals
**Goal:** formalize inboxes and approval workflows.

**Scope**
- Royal Mail inbox/outbox.
- Parent approvals for work verification, covers, and reward usage where needed.
- Notification generation for important events.

**Dependencies**
- Milestones 1-2.

**Acceptance criteria**
- Important actions can create mail.
- Approvals are traceable and tied to accounts.

## Milestone 6: Duties, jobs, bounties, and verification
**Goal:** separate responsibilities from premium work.

**Scope**
- Duty / Job / Bounty / Habit classification.
- Definition of Done and verification states.
- Cover requests and excused/missed outcomes.

**Dependencies**
- Milestones 2-5.

**Acceptance criteria**
- Bounties always require verification.
- Jobs and duties follow explicit workflow states.
- Original assignment history is preserved.

## Milestone 7: Reward inventory and goals
**Goal:** make rewards ownable and reusable.

**Scope**
- Reward inventory instances/quantities.
- Usage/approval tracking.
- Savings and goal transfers using the same Gold currency.

**Dependencies**
- Milestones 1-4.

**Acceptance criteria**
- Purchasing a reward creates inventory instead of only immediate consumption.
- Goals and savings move Gold without creating new currency.

## Milestone 8: Merit, Royal Standing, inventory, and treasure
**Goal:** add non-currency progression systems.

**Scope**
- Merit awards and history.
- Royal Standing states and permissions.
- Item inventory, equipment, treasure, collection book, and cosmetics.

**Dependencies**
- Milestones 2-4.

**Acceptance criteria**
- Merit and Royal Standing affect permissions/unlocks, not spending.
- Inventory and equipment do not impact household wages.

## Milestone 9: Trading and social workflows
**Goal:** support safe item exchanges.

**Scope**
- Trade proposals, recipient acceptance, parent approval, atomic transfers.
- Messaging hooks for social workflows.

**Dependencies**
- Milestones 1-3 and 8.

**Acceptance criteria**
- No player can directly alter another player's inventory.
- Trades are fully auditable.

## Milestone 10: RPG tuning and future expansion
**Goal:** rebalance the existing RPG economy around the new foundation.

**Scope**
- Adjust treasure distribution toward items/cosmetics.
- Ensure RPG Gold stays a minor share of total Gold creation.
- Leave room for overworld/resources/crafting.

**Dependencies**
- Prior milestones.

**Acceptance criteria**
- Existing combat and dungeon behavior still works.
- New economic boundaries remain intact.
