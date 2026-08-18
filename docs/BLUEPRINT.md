# Questboard Derivative Blueprint

## Purpose
Preserve QuestBoard's family RPG loop while adding durable family-management systems: real accounts, server-side permissions, append-only accounting, profiles, approvals, mail, inventory, and future social/economic features.

## Product invariants
- Keep the existing pixel-art RPG identity, monster combat, dungeon, chores, rewards, XP, streaks, and history.
- Gold is the only spendable currency.
- XP, Merit, Royal Standing, inventory items, and resources are not currencies.
- RPG-generated Gold must remain a small minority of total Gold creation over the configured accounting period.
- RPG mechanics must never multiply real Job wages.
- Preserve upstream licensing and attribution.

## Current architecture boundary
- Frontend: React/Vite client owns most UI and gameplay interactions.
- Backend: FastAPI currently persists JSON blobs and should become the source of truth for structured state.
- Storage: move toward SQLite and append-only records before adding auth or advanced workflows.

## Identity and profiles
- Every family member has a real account and password.
- Passwords must never be stored plaintext.
- Parents have elevated administrative roles.
- Logged-in users act only as themselves.
- Other profiles remain visible read-only.
- Profiles should eventually surface Gold, class, level, equipment, inventory, collection progress, reward inventory, chores/jobs, streaks, Merit, Royal Standing, history, and goals.

## Economy
- Gold flows through a ledger, not mutable balances alone.
- Parent deductions move Gold into a visible Kingdom Vault.
- Monster theft should be tracked as a separate game pool/hoard rather than erased value.
- Rewards should increasingly favor items, cosmetics, equipment, and collection pieces over Gold.

## Ledger model
- Every Gold movement becomes an immutable ledger entry.
- No edits or deletes; mistakes use compensating entries.
- Ledger categories should include job, duty bonus, bounty, RPG reward, monster theft, parent award/deduction, reward purchase/refund, correction, savings transfer, and goal transfer.
- Existing balances should later migrate through opening balance transactions.

## Royal Mail
- Each account has an inbox with read/unread state.
- Mail is used for approvals, adjustments, deductions, reward actions, bounty verification, and other important system events.

## Work types
- Duty: baseline responsibility, usually no Gold, with a small daily duty bonus when all required duties are done.
- Job: compensated household labor based on time/difficulty.
- Bounty: premium work that always requires parent verification.
- Habit: learning-oriented work focused on XP, Merit, or mastery.

## Verification and cover requests
- Jobs/quests may require verification or allow self-certification.
- Bounties always require verification.
- Cover requests need parent approval and preserve original assignment history.
- Excused and other workflow states should exist without hard-coding punishment rules too early.

## Rewards, inventory, and treasure
- Purchasing a reward should create owned inventory, not necessarily consume it immediately.
- Track purchased_at, used_at, approval status, and quantity where relevant.
- Treasure should support items, equipment, cosmetics, keys, collection pieces, and occasional small Gold.
- Design inventory and equipment slots so they can expand later.

## Merit and Royal Standing
- Merit is recognition, not currency.
- Royal Standing is a permission state, not a score or currency.
- Both should feed profiles, history, and future unlocks without affecting wages.

## Future-ready boundaries
- Keep room for overworld/resource gathering/crafting later.
- Keep room for trading, gifting, companions, collections, homes, and profile customization later.
- Avoid coupling RPG combat math to household finance math.

## Deferred decisions
- Final Kingdom Vault spending rules.
- Exact reward loot tables and rarity probabilities.
- Final disciplinary policy.
- Exact long-term use of Merit, Royal Standing, and collectibles.
