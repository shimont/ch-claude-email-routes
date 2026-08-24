# ch-claude-email-routes

Backup and analysis of the Claude Routines that manage `shimon@copperhelm.com`.

## Contents

- [`policy/`](policy/) — **the source of truth.** Each routine is an ordered list of fragments;
  `fragments/shared/` holds the 13 blocks daily and deep have in common, so they exist once.
- [`tools/render.py`](tools/render.py) — assembles a routine's prompt. `--verify` proves every
  routine still reproduces its baseline byte-for-byte.
- [`routines/`](routines/) — byte-exact baseline of what is live, plus `manifest.json`
  (trigger IDs, crons, models). `.prompt.txt` is exact; `.md` is the readable view.
- [`ANALYSIS.md`](ANALYSIS.md) — gaps, overlaps and improvements across the three routines.
- [`MIGRATION.md`](MIGRATION.md) — deviation check, cutover plan, and the bootstrap prompt.
- [`proposed/`](proposed/) — the first fix batch, staged for manual application.

```
$ python3 tools/render.py --verify
  daily    55324 ch  OK  matches routines/01-daily-email.prompt.txt
  deep     50340 ch  OK  matches routines/03-deep-sent-scan.prompt.txt
  triage   27851 ch  OK  matches routines/02-4h-triage.prompt.txt

all routines reproduce their baseline byte-for-byte
```

Run that before opening any PR. The fragment split is a relocation of text, never an edit — a real
change must show up as both a fragment diff and a baseline diff.

## Editing a routine

The prompts live in the Routine itself, not in this repo — editing a file here changes nothing on
its own.

Changes must be applied by hand in the claude.ai Routines UI. Agents cannot do it: `update_trigger`
refuses these Routines because they were created via the web UI (`created via "http_api"`), and
recreating them with `create_trigger` produces Routines that carry no MCP connectors, so they run
without Gmail. Both attempts are documented in
[`proposed/CHANGES-2026-08-17.md`](proposed/CHANGES-2026-08-17.md#why-this-cant-be-automated).

After applying any change, re-export so `routines/` matches live state.
