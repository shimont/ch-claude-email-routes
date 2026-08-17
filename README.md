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
- [`proposed/`](proposed/) — ready-to-apply changes.
  - [`CHANGES-2026-08-17.md`](proposed/CHANGES-2026-08-17.md) — cron/model settings plus the
    deep-sent-scan prompt rewrite, with the reasoning for each
  - [`03-deep-sent-scan.prompt.txt`](proposed/03-deep-sent-scan.prompt.txt) — paste-ready prompt
  - [`03-deep-sent-scan.diff`](proposed/03-deep-sent-scan.diff) — what changed vs the backup

## Editing a routine

The prompts live in the Routine itself, not in this repo — editing a file here changes nothing on
its own.

All three Routines were created through the web UI, so the API rejects agent updates
(`created via "http_api"` — agents may only update Routines they created). Changes must be applied
by hand in the Routines UI. After applying any change, re-export so `routines/` matches live state.
