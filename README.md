# ch-claude-email-routes

Backup and analysis of the Claude Routines that manage `shimon@copperhelm.com`.

## Contents

- [`routines/`](routines/) — verbatim backup of the three Routine prompts, with their schedules and
  trigger IDs. Snapshot taken 2026-08-17.
  - [`01-daily-email.md`](routines/01-daily-email.md) — daily follow-up scan, `0 5 * * *`
  - [`02-4h-triage.md`](routines/02-4h-triage.md) — fresh inbound triage, `0 7,11,14,17 * * *`
  - [`03-deep-sent-scan.md`](routines/03-deep-sent-scan.md) — 7–30 day sent scan, `0 9 * * 1,4`
  - [`manifest.json`](routines/manifest.json) — trigger IDs, crons, environment and model config
- [`ANALYSIS.md`](ANALYSIS.md) — gaps, overlaps and suggested improvements across the three.

## Restoring or editing a routine

The prompts live in the Routine itself, not in this repo — editing a file here changes nothing on
its own. To apply a change, update the Routine via `update_trigger` using the trigger ID in
`manifest.json`, then re-run the backup so this repo stays in sync.
