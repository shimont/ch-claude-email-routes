# Migrating to repo-backed routines

Status as of **2026-08-24**. Read [`ANALYSIS.md`](ANALYSIS.md) first for why; this is the how.

## 1. Deviation check

Live Routines were re-fetched and compared against the 2026-08-17 snapshot.

### Prompts: no drift

All three live prompts are **byte-identical** to what is in `routines/*.prompt.txt`. Nothing
edited them, and nothing I did touched them.

> The earlier `routines/*.md` backups showed a 2-character difference. That was an artifact of my
> own export wrapping the text in a fenced block, not drift. `routines/*.prompt.txt` now holds the
> byte-exact prompt and the `.md` files stay as the readable view.

### Settings: two changed since the snapshot

| Routine | Field | Snapshot 2026-08-17 | Live now | Note |
|---|---|---|---|---|
| daily email | model | `claude-opus-4-8` | `claude-opus-5` | matches the recommendation |
| deep sent scan | model | `claude-opus-4-8` | **`claude-fable-5`** | different tier from the other two |
| deep sent scan | `updated_at` | 2026-08-17 11:55 | 2026-08-23 21:19 | |
| daily email | `updated_at` | 2026-08-17 11:48 | 2026-08-23 21:09 | |
| 4h triage | — | — | unchanged | still `claude-opus-5` |

So the model alignment (item 4) was applied on 2026-08-23, with the deep sent scan going to
`claude-fable-5` rather than `claude-opus-5`. Worth a conscious decision either way: that routine
is the heaviest of the three — it pages ~400 sent threads, reconciles shard counts, and pulls
transcripts — and it now runs on a different model from the two it shares 98% of its text with.

**Items 1–3 were not applied.** Both crons are unchanged (`0 9 * * 1,4`, `0 7,11,14,17 * * *`) and
the deep sent scan still carries the self-contradicting prompt.

### My own rewrite: verified clean

`proposed/03-deep-sent-scan.prompt.txt` was re-verified section by section against the **live**
prompt. Every section I claimed untouched is byte-identical — `COPPERHELM BLURB`, `CALL CONTEXT`,
`GATE`, `BUCKETS`, `SELF-ADDRESSED NOTES`, `NEVER FLAG`, `URGENCY`, `GONE-DARK`, `DRAFTS`, and both
trailer batches. Only the seven documented sections changed. One stray trailing newline was found
and trimmed.

## 2. The constraint

Routines can only be created or edited in the **claude.ai Routines UI**. Verified, both paths:

- `update_trigger` refuses every field on all three (`created via "http_api"`) — including rename
  and disable.
- `create_trigger` succeeds but the result stores **no MCP connectors**, and the `connectors`
  parameter is unavailable for this org, so a recreated Routine runs without Gmail and stops on its
  own first instruction.

The migration therefore has exactly **one** manual UI step per routine, and it is the last one you
ever need to take.

## 3. The design

Today each routine carries its whole policy inline: 55k, 28k and 50k characters, with daily and
deep sharing 98% of their text and already drifting apart. Instead, the prompt becomes a ~15-line
bootstrap and the policy lives here.

```
policy/
  01-daily-email.json        ordered fragment list per routine
  02-4h-triage.json
  03-deep-sent-scan.json
  fragments/
    shared/…                 13 fragments used by BOTH daily and deep (~38k chars, one copy)
    daily/… triage/… deep/…  fragments unique to one routine
routines/*.prompt.txt        byte-exact baseline of what is live right now
tools/render.py              assembles a prompt; --verify proves the split is lossless
```

```
$ python3 tools/render.py --verify
  daily    55324 ch  OK  matches routines/01-daily-email.prompt.txt
  deep     50340 ch  OK  matches routines/03-deep-sent-scan.prompt.txt
  triage   27851 ch  OK  matches routines/02-4h-triage.prompt.txt

all routines reproduce their baseline byte-for-byte
```

That assertion is the safety property. The split is a **pure relocation of text** — never an edit.
Any real change shows up as a fragment diff *and* a matching baseline change, so a migration bug
can never hide inside a behaviour change.

Two things fall out immediately:

- **The 98% duplication is gone.** `shared/drafts.txt` (13,940 chars), `shared/gate.txt`,
  `shared/self-check.txt` and 10 others exist once. Editing `DRAFTS` now changes both routines by
  construction — the class of bug in §C1 of the analysis becomes impossible.
- **The drift is visible.** `NOISE SWEEP` did *not* land in `shared/`, because deep's copy differs
  from daily's — that is exactly the missing billing-failure protection. The tool found it
  mechanically rather than by inspection.

Triage shares zero fragments today; its versions of `GATE`, `DRAFTS` and the rest genuinely differ.
Converging them is a later reviewed change, not part of this migration.

## 4. Cutover

**The cardinal rule: never two writers on one mailbox.** Duplicate drafts have already happened
three times (Martin Stanley/NIST 29 seconds apart, Beville/Amazon, Aphinia) and there is no
delete-draft tool. So: **one routine at a time, old disabled before new is enabled.**

Order — lowest cadence and smallest blast radius first:

**1. deep sent scan** (2×/week) → **2. 4h triage** (4×/day, 2-day window) → **3. daily email**
(1×/day, widest scope)

For each routine:

| # | Step | Where |
|---|---|---|
| 1 | `python3 tools/render.py deep` — confirm it prints the full prompt | here |
| 2 | Create a new Routine, **attach `shimont/ch-claude-email-routes` as its source**, paste the bootstrap below, set the cron and model | Routines UI |
| 3 | Leave it **disabled**. Fire it once manually and read the output | Routines UI |
| 4 | Confirm it reports the git commit it rendered from, and that its behaviour matches the old routine's last run | output |
| 5 | **Disable the old routine**, then enable the new one — in that order | Routines UI |
| 6 | Watch one real scheduled run before starting the next routine | |

If step 3 fails because the session cannot reach the repo, stop and use the fallback in §6.

Migrate **byte-identical first**, then merge the deep-sent-scan fix as a policy PR. Two verifiable
steps beat one ambiguous one — and the fix needs no further UI touch, which is the whole point.

## 5. The bootstrap prompt

Paste this as the entire Routine prompt, substituting `deep` → `daily` / `triage`.

```text
POLICY-BACKED ROUTINE - deep sent scan (Shimon Tolts, Copperhelm)

Your instructions are NOT in this prompt. They live in the git repository
shimont/ch-claude-email-routes. Load them before doing anything else:

1. Find the repo checkout attached to this session. Try the working directory, then:
   find / -maxdepth 4 -name ch-claude-email-routes -type d 2>/dev/null
   If it is genuinely absent, clone it:
   git clone https://github.com/shimont/ch-claude-email-routes
2. cd into it and run: git pull --ff-only
3. Run: python3 tools/render.py deep
4. The text it prints IS your complete instruction set. Follow it exactly, as though it
   had been pasted here in full. It supersedes nothing in it is optional.

FAIL-STOP (BLOCKING): if the repo cannot be read, or render.py errors, or it prints fewer
than 20000 characters, STOP THE RUN IMMEDIATELY. Do not improvise, do not work from
memory, do not create or modify a single draft or label, do not tag anything. Report
"POLICY LOAD FAILED" with the error and end the run. A run on half-remembered rules is
worse than no run at all.

At the end of your output, state the policy version you ran:
  git rev-parse --short HEAD
```

The fail-stop is the important part. Without it, a session that cannot read the repo would fall
back on whatever it remembers about triaging email and start writing drafts — the one failure mode
that is worse than the routine not running.

Set the cron and model in the UI as usual. Recommended at creation time, from
[`proposed/CHANGES-2026-08-17.md`](proposed/CHANGES-2026-08-17.md):

| Routine | cron (UTC) | model |
|---|---|---|
| deep sent scan | `0 21 * * 1,4` | decide: `claude-fable-5` (current) or `claude-opus-5` |
| 4h triage | `0 7,11,15,20 * * *` | `claude-opus-5` |
| daily email | `0 5 * * *` | `claude-opus-5` |

## 6. If a fired session cannot reach the repo

Whether a trigger-fired session gets the checkout depends on attaching the repo when the Routine is
created, and I could not verify that from here — step 3 of the cutover is what settles it.

If it turns out it cannot, the repo still works as the source of truth; only the delivery changes.
Run `python3 tools/render.py <routine>` and paste the output into the UI. You keep single-source
policy, reviewed diffs and the losslessness check, and give up only the no-touch updates. Do **not**
respond by hand-editing prompts in the UI — that is how the current drift happened.

## 7. Working on it after the migration

Every change becomes an ordinary PR:

1. Edit a fragment under `policy/fragments/`.
2. Update the matching `routines/*.prompt.txt` baseline (that is the reviewable diff).
3. `python3 tools/render.py --verify` — must pass.
4. Open a PR. The diff shows exactly which rules changed and which routines inherit them.
5. Merge. The next scheduled run picks it up; no UI, no pasting.

Because each run reports the commit it rendered from, a bad run is traceable to an exact policy
version, and rolling back is `git revert`.

The queued work, from [`ANALYSIS.md`](ANALYSIS.md) §G — each is now a small fragment edit rather
than a 50,000-character re-paste:

| Item | Fragment | Fixes |
|---|---|---|
| deep-scan contradiction | `deep/*` | §A1 — already prepared in `proposed/` |
| billing-failure drift | `deep/noise-sweep.txt` | §C1 — or delete the sweep with the fix above |
| stale-tag rule | `shared/ready-to-archive-tagging.txt` | §B1 — both routines at once |
| unsent-draft ageing | `shared/drafts.txt` | §B2 |
| terminal sweep moves to daily | `daily/*`, `deep/gone-dark.txt` | §B3 |
| teammate-outbound sweep | `daily/scope-pre-filter.txt` | §B4 |
| converge triage onto shared fragments | `triage/*` | §C1 — one rule at a time, each reviewed |
