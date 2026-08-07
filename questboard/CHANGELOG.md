# Changelog

## 1.12.6 - 2026-08-06

### Fixed
- **History tab per-player filter** now correctly matches entries across player name
  changes. Filter buttons key on player ID; older entries without an ID fall back to
  name matching so nothing is lost.
- **Weekly quest reset label** now shows the actual configured week-start day (e.g.
  "resets Monday") instead of the hardcoded "resets Sunday".
- **Dungeon hero tiles** for Rogue and Paladin were swapped. They now derive directly
  from `data.js` so the two sets of tile indices can never drift apart again. Ranger
  and Frost Knight fall back to the Warrior tile rather than an incorrect value.
- **Bounty gold input** no longer allows typing a reward higher than the player's
  current gold balance.
- **Backend state writes** are now atomic: data is written to a `.tmp` file and
  renamed into place, so a crash mid-write cannot corrupt `state.json` or
  `config.json`. Both POST endpoints also reject non-object payloads.

### Changed
- History entries now store `playerId` alongside `player` (name) so per-player
  filtering stays correct even if a player is renamed.
- History tab reversal and slice are now memoised so they don't re-run on every
  unrelated render.

## 1.12.5 - 2026-08-06

### Added
- **Weekday/weekend chore scheduling** (Settings → Quests): daily chores can now
  be limited to weekdays only (**WD**), weekends only (**WE**), or every day
  (**7d**, the default). The toggle appears on each daily chore row in the quest
  picker and on the custom chore form. Chores hidden by the schedule are fully
  excluded from the game loop — no phantom midnight penalties.
- **Admin PIN** (Settings → Display): optionally lock Settings, Reset week, and
  Import Save behind a 4-digit PIN to prevent kids from accidentally changing
  configuration. Leave the field blank to disable the lock entirely. The PIN
  unlocks for the browser session so parents aren't re-prompted on every tap.
  Export Save remains unprotected (read-only action). This is a convenience lock,
  not a security system.
- **Personal device focus** ("This is me"): tap the **📌 This is me** button on
  any hero card to pin that device to your hero. The board collapses to show only
  your card, you're auto-selected, and your choice persists across page reloads
  via `localStorage`. Tap **⇄ Switch player** (below your card) to return to the
  full family view. No backend or account changes — purely device-local.

## 1.12.4 - 2026-06-28

### Added
- Vacation mode (Settings → Display): pause overnight monster penalties while the
  family is away from home. Toggle it on with an optional From/To date range, or
  leave the dates blank to pause penalties indefinitely until switched off. On
  covered days the monster doesn't strike back (no gold penalty) and kill streaks
  are frozen rather than reset.

### Changed
- The Heroic/Epic UI scale now zooms only the foreground content, leaving the
  full-screen dungeon background and torches at true viewport size so they render
  correctly.
- At Epic scale the secondary toolbar (Sound/Settings/Reset week/Export/Import)
  collapses into a hamburger menu so it no longer overflows the viewport; each
  toolbar action also gets its own icon.
- Swapped the solo/party chore labels so they match how players read them: **ALL**
  now means every player does their own copy, **1P** means one person does it for
  the party. Underlying data/logic keys are unchanged.

### Fixed
- Static monster sprites now honor their configured color filter, so palette-shifted
  monster variants render in the correct colors.
- The browser tab title now reads "Questboard" to match the app branding.

## 1.12.3 - 2026-06-26

### Fixed
- Weekly quests with a scheduled day (Recycling, Take out trash) were hidden on
  every other day of the week, so they appeared to be permanently missing from
  the quest list regardless of audience or scope. Weekly quests are now shown
  every day for matching players.

## 1.12.2 - 2026-06-26

### Changed
- Performance: the animated dungeon background now scrolls via GPU-composited
  transforms instead of per-frame background-position repaints, and its color
  filters are rasterized once instead of every frame. The static vignette/wall/
  torch-glow lighting is painted once per resize rather than redrawn each frame.
  Parallax layers now also loop seamlessly at any viewport height. No visual or
  gameplay changes.

## 1.12.1 - 2026-06-26

### Changed
- Performance: optimized rendering for low-end devices. Memoized the most-rendered
  components (TileSprite, MonsterSprite, chore/reward grids) so unrelated state
  changes no longer reconcile the whole tree, and code-split the heavy views
  (SetupWizard, DungeonMap, BountyBoard, HistoryTab) to shrink initial parse cost.
  No gameplay or animation changes.

## 1.0.0 - 2026-05-24

### Added
- Initial release
- Pixel art RPG-themed chore tracking for up to 6 players
- Daily, weekly, and monthly chore quests
- Monster battle system - complete chores to damage your assigned monster
- Crit system with 5% base chance, scales with player level
- XP and leveling system
- Gold rewards for defeating monsters, penalty if defeated by midnight
- Reward shop for spending gold on family treats
- History log of all chore and reward activity
- Multi-arch Docker image (amd64, aarch64, armv7)
- Home Assistant ingress support (no port forwarding required)
