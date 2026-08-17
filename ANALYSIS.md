# Email routine analysis — 2026-08-17

Analysis of the three Routines that write into `shimon@copperhelm.com`. Prompts as backed up in
[`routines/`](routines/); line references point at those files.

## Inventory

| # | Routine | Cron (UTC) | Local (Israel) | Owns | Prompt size | Model |
|---|---------|-----------|----------------|------|-------------|-------|
| 1 | [daily email](routines/01-daily-email.md) | `0 5 * * *` | 08:00 daily | `in:inbox 30d` + `in:sent 7d` | 55,326 ch / 629 lines | `claude-opus-4-8` |
| 2 | [4h triage](routines/02-4h-triage.md) | `0 7,11,14,17 * * *` | 10:00 14:00 17:00 20:00 | `in:inbox 2d` | 27,853 ch / 337 lines | `claude-opus-5` |
| 3 | [deep sent scan](routines/03-deep-sent-scan.md) | `0 9 * * 1,4` | 12:00 Mon + Thu | `in:sent 7-30d` | 50,342 ch / 571 lines | `claude-opus-4-8` |

Shared coordination state is only Gmail: the `READY-TO-ARCHIVE` label
(`Label_5913419933435317385`), the draft-exists gate, and the single-writer ownership table added
2026-08-17 after two duplicate drafts landed on the Martin Stanley / NIST thread 29 seconds apart.

**Ownership table** (identical in all three, keyed on the thread's newest non-draft message):

| Newest non-draft message | Owner |
|---|---|
| Inbound, < 2 days | 4h triage |
| Inbound, ≥ 2 days | daily email |
| Outbound `@copperhelm.com`, < 7 days | daily email |
| Outbound `@copperhelm.com`, 7–30 days | deep sent scan |

The design is sound. Most of what follows is about the gap between that table and what the three
prompts actually *do*.

---

## Executive summary

The eight things worth fixing, in order of payoff:

1. **The deep sent scan contradicts itself on every run** — its scope override disowns the inbox
   scan, noise sweep and intro reconciliation, but the inherited body still orders all three, and
   its own mandatory self-check demands a reconciliation it structurally cannot pass. Fix is pure
   deletion. (§A1)
2. **`READY-TO-ARCHIVE` is a permanent mute with no staleness rule** — the stale-*draft* case is
   handled in all three prompts; the stale-*tag* case is handled nowhere, so a tagged thread that
   comes back to life is skipped forever. Live instance in the mailbox today. (§B1)
3. **An unsent draft freezes a thread for 27 days and then gets it archived as "gone dark"** — the
   draft-exists gate never expires, and the aging-out rule doesn't exempt threads with a pending
   draft. (§B2)
4. **Aging-out depends on a twice-weekly routine**, so threads can cross the 30-day horizon
   untagged on the exact path the prompts call a run failure. (§B3)
5. **Teammate-sent-last threads are in scope but unreachable** — the only outbound scan is
   `in:sent`, which contains only Shimon's sends. The three real misses named in the prompt are
   all exactly this shape. (§B4)
6. **daily and deep are 98% the same text and have already drifted** — 49,186 of 50,342 characters
   shared, with a safety rule present in two prompts and missing from the third. (§C1)
7. **Cron windows overlap and ownership is keyed on a value that changes mid-run**, so the
   duplicate-draft race the 2026-08-17 rules were written to stop is still open. (§D1)
8. **Rule inflation** — 14 `BLOCKING` + 12 `FAILURE` + 10 `MANDATORY` markers in the daily prompt
   alone. When everything is top priority, nothing is, and budget goes to proving compliance
   instead of processing threads. (§E1)

---

## A. Contradictions inside a single routine

### A1. The deep sent scan orders work its own scope override forbids — HIGH

The override at [`03:14-21`](routines/03-deep-sent-scan.md#L14) is explicit: the only scan is
`in:sent older_than:7d newer_than:30d`, and it says to **skip entirely** the inbox reply scan, the
"commitments I made" scan, the noise sweep and the "Intro: Copperhelm" reconciliation. The body it
was cloned from still commands every one of them:

| Line | Surviving instruction | Conflict |
|---|---|---|
| [`03:43`](routines/03-deep-sent-scan.md#L43) | "Review my inbox for items that need MY follow-up." | The routine's opening directive is the thing the override disowns |
| [`03:52-54`](routines/03-deep-sent-scan.md#L52) | "run the NOISE SWEEP at the end" | Override says skip it |
| [`03:55-58`](routines/03-deep-sent-scan.md#L55) | "run ONE global search (`in:inbox newer_than:30d`) … verify … inbox processed vs inbox total" | Cannot pass: it processes no inbox threads |
| [`03:64-67`](routines/03-deep-sent-scan.md#L64) | "Reply scan: `in:inbox newer_than:30d`" | Override says skip it |
| [`03:133-144`](routines/03-deep-sent-scan.md#L133) | Intro reconciliation, "missing from all four buckets is a RUN FAILURE" | Override says skip it |
| [`03:231-259`](routines/03-deep-sent-scan.md#L231) | Full 2,039-char noise sweep section | Override says skip it |
| [`03:508-511`](routines/03-deep-sent-scan.md#L508) | Self-check 7 requires both reconciliations | Same impossible check, restated as mandatory |

Every Mon/Thu run therefore resolves one of two ways: it obeys the body and burns its budget
redoing the daily routine's work on the day it can least afford to (it also has ~400 sent threads
to page), or it obeys the override and **fails a check labelled mandatory**. The second is the
worse outcome, and not because of the run it happens on: a routine that fails a mandatory check
every single time teaches the model that failing mandatory checks is the normal end state, which
devalues the other 11 `BLOCKING` markers in the same prompt.

**Fix:** delete the disowned sections outright rather than overriding them in a preamble — the
inbox reply scan, the noise sweep, the intro reconciliation, the inbox half of shard completeness,
and self-check 7's inbox clause. Rewrite `03:43` to say "review my **sent** mail". Nothing else in
the routine depends on them.

### A2. Formatting damage from repeated in-place edits — LOW

At [`01:43-45`](routines/01-daily-email.md#L43) and [`03:52-54`](routines/03-deep-sent-scan.md#L52),
"Read-only analysis; create drafts only, never send. Apply the READY-TO-ARCHIVE label … and run the
NOISE SWEEP at the end" sits mid-sentence inside the shard-ownership paragraph, where it has
nothing to do with sharding. Both files show the same seam. Symptomatic: the prompts are being
patched by append without re-reading, which is exactly the process that produces §C1.

---

## B. Coverage gaps — cases no routine owns

### B1. A stale `READY-TO-ARCHIVE` tag mutes a thread permanently — HIGH

All three prompts treat the tag as terminal:

- triage idempotency skip #2 — "already tagged `READY-TO-ARCHIVE` → SKIP"
  ([`02:64-65`](routines/02-4h-triage.md#L64))
- the sent-scan condition (c) requires "no draft and no `READY-TO-ARCHIVE` tag already exist"
  ([`01:63-66`](routines/01-daily-email.md#L63), [`03:73-80`](routines/03-deep-sent-scan.md#L73))
- the post-call path explicitly refuses to revive a tagged thread
  ([`01:181-183`](routines/01-daily-email.md#L181))

The stale-**draft** case is handled carefully in all three ("if the draft is OLDER than the newest
message … list under needs-human-review"). The stale-**tag** case is handled nowhere. So a thread
correctly tagged done in July, which gets a live inbound in August, is skipped by triage, excluded
by the sent scan, and refused by the post-call path.

This is live in the mailbox now. Thread `19fd5abeff764b08` (`jacob.riff@getklaay.ai`) carries
`Label_5913419933435317385` on its Aug 6 message and has a fresh Aug 17 inbound sitting in `INBOX`.
That specific thread may well be a vendor cadence that *should* be ignored — the mechanism is the
point, not the counterparty.

Two things make it hard to spot: Gmail evaluates `label:` and `in:inbox` **per message**, so
`label:READY-TO-ARCHIVE in:inbox` returns nothing for exactly this shape (verified — it returns
empty while the case above exists); and the prompts never say whether the tag is a thread property
or a message property, though `label_thread` and the search semantics disagree.

**Fix:** mirror the stale-draft rule. A tag is void if any non-draft message postdates it. Gmail
exposes no "labelled at" timestamp, so make the newest message the carrier: apply the label with
`label_thread` (all messages), and treat *"the thread's newest non-draft message does not carry the
label"* as a void tag → re-evaluate normally and `unlabel_thread`. Cheap, uses data already
fetched for the ownership decision.

### B2. An unsent draft freezes a thread, then converts it to "gone dark" — HIGH

The draft-exists gate is unconditional and has no age
([`01:378-385`](routines/01-daily-email.md#L378),
[`02:56-63`](routines/02-4h-triage.md#L56),
[`03:319-327`](routines/03-deep-sent-scan.md#L319)) — the only escape is a *newer inbound message*.
If the counterparty stays silent, which is the whole premise of a nudge thread, the draft blocks
that thread indefinitely. Meanwhile the aging-out rule
([`01:361-363`](routines/01-daily-email.md#L361),
[`03:303-305`](routines/03-deep-sent-scan.md#L303)) tags any self-sent-last no-reply thread at 27
days as `READY-TO-ARCHIVE` / "gone dark (aged out)" — with no exemption for a pending draft.

End state: a draft Shimon never got round to sending silently becomes an archived dead thread, and
the run output reports it as gone dark rather than as *never sent*.

Currently latent, not active — `list_drafts` shows **one** pending draft in the whole mailbox
(`gottemi@gmail.com`, created 05:38 today), so drafts are being cleared fast. Worth fixing before
a busy week makes it real.

**Fix:** (a) every run lists pending drafts older than 2 business days under "unsent — your move",
with age; (b) never tag a thread aged-out/gone-dark while it carries a pending draft — surface it
as "draft written, awaiting send".

### B3. Aging-out is owned by a twice-weekly routine — MEDIUM-HIGH

Outbound-latest threads in the 7–30 day band belong solely to the deep sent scan, which runs Mon
and Thu. A thread reaching 27 days on a Friday isn't looked at until Monday, when it is 30 days old
and no longer matches `newer_than:30d` — so it leaves the window untagged and untracked, which both
prompts call out as the thing that must never happen ("never let a thread leave the window
untagged").

Compounding it: the 7d and 30d edges use relative `older_than:` / `newer_than:`, which Gmail rounds
to whole days. The seam between "daily owns < 7d" and "deep owns 7–30d" is therefore fuzzy by up to
a day, in both directions.

**Fix:** move the terminal sweep (aged-out + nudge-cap tagging) to the **daily** routine over a
25–30 day band — it runs every day and the sweep is cheap. Widen the deep scan to
`newer_than:35d` so the boundary overlaps instead of butting. Compute explicit `after:` / `before:`
dates per run rather than relying on relative operators.

### B4. Teammate-sent-last threads are in scope but undiscoverable — MEDIUM-HIGH

Month-audit rule 1 ([`01:599`](routines/01-daily-email.md#L599),
[`03:541`](routines/03-deep-sent-scan.md#L541)) puts outbound from **any** `@copperhelm.com`
address in scope, and the ownership table routes "outbound" by age. But the only outbound scan is
`in:sent`, which contains only Shimon's own sends. A thread where Reut or Roman sent last is
visible only while it happens to sit in Shimon's inbox.

The three real misses the rule cites — Myke Lyons' advisor agreement, Pieter van Iperen's
agreement, the Security Unfiltered reschedule, "all sent by Reut, all went silent untracked" — are
all this shape, so the rule was written without the scan that would find them. The rule reads as
satisfied; nothing implements it.

**Fix:** add one sweep to the daily routine:
`from:copperhelm.com -from:shimon@copperhelm.com newer_than:30d -in:sent` (and consider
`in:anywhere` to catch archived ones). Route hits to needs-human-review as the prompt already
specifies — "ping `<teammate>` or nudge personally" — never auto-draft from Shimon's account.

### B5. No escape hatch past the 30-day horizon — MEDIUM

30 days is the whole tracking universe. The deferral rule
([`01:214-221`](routines/01-daily-email.md#L214)) tops out at 10 business days, and anything else
that needs re-engagement later — "revisit in Q4", "after our budget cycle", "ping me when you have
SOC 2" — ages out at 27 days and gets tagged gone-dark. For enterprise cycles that is the normal
case, not the edge case.

**Fix:** a `FOLLOW-UP-LATER` label carrying a target date, excluded from aging-out, swept by a
cheap weekly or monthly routine; or push the long-dated ones into HubSpot tasks, which the routines
already touch.

### B6. The 2-day ownership boundary can strand a thread for ~24h — MEDIUM

Inbound lands 06:00 UTC Monday. The Wednesday 05:00 daily run sees it as < 2 days → "triage owns
it, skip". At 06:00 Wednesday it crosses 2 days, so from the 07:00 triage run onward triage says
"daily owns it, skip". Nothing acts until Thursday 05:00.

Hand-off protection exists for this ([`01:29-32`](routines/01-daily-email.md#L29),
[`03:38-41`](routines/03-deep-sent-scan.md#L38)) but (a) it is **absent from the triage prompt**,
the routine on the near side of this particular boundary, and (b) it only promotes priority — it
never authorises acting outside your band, so it cannot close a hole *between* bands.

In practice triage usually drafts fresh inbound on first sight, so this mostly bites threads triage
declined for a soft reason ("when in doubt, don't flag") and then never re-examines.

**Fix:** make the boundary a soft overlap — a routine may act on a thread within 6 hours of its
boundary if no draft exists. Or simply give triage the ≥2d inbound band as well: it runs 4× a day
and already carries the same gates, and that removes the boundary rather than patching it.

### B7. Reconciliation counts against an unreliable denominator — MEDIUM

Shard completeness turns on "run ONE global search and count threads"
([`01:46-51`](routines/01-daily-email.md#L46), [`03:55-61`](routines/03-deep-sent-scan.md#L55)).
The API returns `resultCountEstimate`, and it looks capped: two very different queries
(`label:READY-TO-ARCHIVE`, `in:inbox newer_than:30d`) both returned exactly `201`. If a run reads
that as the true total, the reconciliation either passes vacuously or chases a phantom gap.

**Fix:** state that the denominator must come from paging to exhaustion (`nextPageToken` until
empty), never from `resultCountEstimate`.

---

## C. Overlap and duplication

### C1. daily and deep are 98% identical, and have already drifted — MEDIUM

Measured on the prompt bodies:

| Pair | Shared characters | % of smaller prompt |
|---|---|---|
| daily ↔ deep | 49,186 | **98%** |
| daily ↔ triage | 12,435 | 45% |
| triage ↔ deep | 14,187 | 51% |

`DRAFTS`, `SELF-CHECK`, `GATE`, `BUCKETS`, `NEVER FLAG` and `CALL CONTEXT` are **byte-identical**
between daily and deep — ~21 KB of copy-paste maintained in two places, with a third partial copy
in triage. The predicted consequence has already happened:

- **Safety rule missing in one copy.** The 2026-08-08 protection for billing/payment failure
  notices ("card declined, payment failed, account at risk — these are real `[OPS]` items; surface
  under needs-human-review instead of tagging") is in daily's noise sweep
  ([`01:295-298`](routines/01-daily-email.md#L295)) and in triage's
  ([`02:178-180`](routines/02-4h-triage.md#L178)) — and **absent from deep's**
  ([`03:249-258`](routines/03-deep-sent-scan.md#L249)). Deep still runs a noise sweep per its own
  body (§A1), so it can tag a card-declined notice the other two are written to protect.
- **Dangling cross-reference.** Deep keeps CALL CONTEXT's `GATE HOOK`
  ([`03:129-131`](routines/03-deep-sent-scan.md#L129)) pointing into post-call reconciliation
  machinery it doesn't have — daily's `POST-CALL RECONCILIATION`
  ([`01:135-189`](routines/01-daily-email.md#L135)) exists in daily only.
- **`INVITES AND PERSONAL FYI`** ([`01:309-317`](routines/01-daily-email.md#L309)) — daily only.
  Unaccepted invites are surfaced once a day at 08:00 and never by the routine that runs 4× a day.
- **HubSpot new-deal-owner high-signal exception** ([`02:166-171`](routines/02-4h-triage.md#L166))
  — triage only; daily and deep tag HubSpot notices with only the demo-form-lead exception, so a
  "made you the Deal owner of SAP" notice is high-signal to one routine and noise to the other two.
- **`BUSINESS DAYS` definition** — daily and deep only, while triage's own month-audit rule 3
  depends on "3 business days" ([`02:340`](routines/02-4h-triage.md#L340)) with the definition
  nowhere in its prompt.

Any future edit has to be applied three times, correctly, by hand. That is the root cause of most
of this document.

### C2. The noise sweep runs up to three times over the same mail — LOW (cost)

daily sweeps the 30-day window every day; triage sweeps the 2-day window 4× a day; deep sweeps the
30-day window again Mon/Thu, using the stale list from §C1. Tagging is idempotent so nothing breaks
— it is pure cost, on the runs that can least afford it.

**Fix:** triage owns the 2-day sweep (fast noise clearance), daily owns a 30-day backfill sweep,
deep owns none.

### C3. daily pages the full 30-day inbox to then skip what triage owns — LOW (cost)

Scope is `in:inbox newer_than:30d` ([`01:54`](routines/01-daily-email.md#L54)) while its band is
inbound ≥ 2 days. Every day it reads the < 2 day threads and discards them.

**Fix:** narrow to `in:inbox older_than:2d newer_than:30d`, keeping the noise sweep on the full
window.

---

## D. Concurrency and scheduling

### D1. Crons overlap, and ownership is keyed on a value that changes mid-run — MEDIUM-HIGH

Ownership is decided by "the thread's NEWEST NON-DRAFT message" — a value that changes when mail
arrives, i.e. during the run. And the runs are long: daily must page a 30-day inbox plus a 7-day
sent window and pull Granola transcripts, starting at 05:00 UTC, while triage fires at 07:00 UTC
and deep at 09:00 UTC Mon/Thu. Overlap is the expected case, not the exception.

The mitigation is the last-second claim re-check
([`01:437-442`](routines/01-daily-email.md#L437), [`02:214-219`](routines/02-4h-triage.md#L214),
[`03:379-384`](routines/03-deep-sent-scan.md#L379)) — re-run `list_drafts` for
`to:<primary recipient>` immediately before `create_draft`. It is per-*recipient* rather than
per-thread, `list_drafts` is subject to propagation lag, and two routines can both pass it inside
the same second. The prompts state the position correctly — "prevention is the only cure, because
duplicates cannot be deleted by any tool available to this routine" — and then rely on a check that
cannot prevent, only narrow. The 29-second Martin Stanley collision is what this looks like when it
loses.

**Fix, in order of effort:**

1. **Stagger so the windows cannot overlap.** Move deep to `0 21 * * 1,4` (after the day's work,
   nothing else running) and triage off the daily start hour, e.g. `0 3,11,15,20 * * *`. Free, and
   removes most of the race.
2. **A real mutex.** The routines have `Bash` and this repo. A claim file — `state/claims.jsonl`,
   one line per `(threadId, routine, timestamp)`, committed before drafting with
   `pull --rebase` + push retry — is atomic in a way `list_drafts` is not: the loser of a push race
   finds out it lost and aborts. This is the only construct available here that actually prevents.
3. **Single writer.** One routine per cron slot, roles as phases inside it. Eliminates the class,
   at the cost of the 4-hour cadence on fresh inbound.

### D2. Triage is blind through the entire US afternoon — MEDIUM

`0 7,11,14,17 UTC` = 03:00, 07:00, 10:00, 13:00 **ET**. Nothing runs between 13:00 ET and 03:00 ET
the next day — a 14-hour blind spot covering the whole US business afternoon, for a US-focused
sales motion. Spacing is also lopsided: 4h, 3h, 3h, **14h**.

**Fix:** add a run at `20` or `21` UTC (16:00/17:00 ET) so US-afternoon inbound is triaged the same
day. `0 7,11,15,20 * * *` spreads it to 4h/4h/5h/11h.

### D3. Model split across routines — LOW-MEDIUM

triage runs `claude-opus-5`; daily and deep run `claude-opus-4-8` — the two longest, densest,
most reconciliation-heavy prompts are on the older model. Reads like an artifact of when each was
last edited rather than a decision. See [`routines/manifest.json`](routines/manifest.json).

---

## E. Prompt structure

### E1. Everything is BLOCKING, so nothing is — MEDIUM

| Prompt | Lines | `BLOCKING` | `FAILURE` | `MANDATORY` | `NEVER` |
|---|---|---|---|---|---|
| daily | 629 | 14 | 12 | 10 | 19 |
| triage | 337 | 9 | 7 | 4 | 16 |
| deep | 571 | 12 | 10 | 10 | 18 |

Roughly 40% of each prompt is post-mortem narrative — "real case", "real miss", "fixes the X slip",
with names and dates. It is valuable history and it is why the rules are trusted, but as *prompt
text* it competes for attention with the instruction it justifies, and it grows monotonically: every
incident adds a paragraph, nothing is ever removed.

The prompts already record the symptom — runs that stall, runs that "produced 6 drafts and silently
dropped 7 known candidates". A routine spending its budget proving compliance with 14 blocking
gates has less left for threads.

**Fix:**

- **Hard invariants, ≤ 7, at the top, nothing else marked blocking:** never send; never draft to an
  `@copperhelm.com` address; one draft per thread; HubSpot BCC on every draft; non-empty body;
  scheduling drafts carry the grid; `replyToMessageId` = newest non-draft message.
- Everything else becomes prioritised heuristics, in plain declarative form.
- **Move the post-mortems out of the prompt** into `reference/postmortems.md`, keyed by rule ID, to
  be read on demand. The rule stays; the story becomes a citation. This alone should cut each
  prompt by a third without losing a single decision.

### E2. Self-checks that cannot be performed — LOW

Several checks ask for verification the prompt itself says is impossible — self-check 2 requires
confirming a draft's anchor while noting "the API cannot reveal a draft's anchor after creation",
and self-check 1 requires re-reading draft bodies while noting the drafts API "does not return
reply-draft bodies and rewraps links on read-back". Combined with §A1's impossible reconciliation,
a meaningful share of the self-check block is re-assertion of intent rather than verification.

**Fix:** keep only checks with an observable signal, and phrase construction-time obligations as
construction-time steps rather than after-the-fact audits. A short honest checklist gets run; a
long one that cannot pass gets pattern-matched.

### E3. Unverified folklore repeated in three places — LOW

All three prompts carry: "KNOWN BUG: searching `label:<labelId>` returns empty even when threads are
tagged; only the name form works." The Gmail tool's own documentation says the opposite — that
`label:` takes label IDs, not display names. The name form does work (verified today). The id form
is untested. Worth one experiment, with the answer recorded once in the shared policy rather than
asserted three times.

---

## F. Recommended structure

The single change that removes most of §C and makes §A survivable is to stop keeping the policy in
the Routine prompts. The routines run in a CCR environment with `Bash` and `Read`, and this repo
now exists.

```
policy/
  00-invariants.md      # the <=7 hard rules. Short.
  10-common.md          # voice, blurb, call context, gates, drafts, scheduling, never-flag
  20-daily.md           # scope + ownership band + output deltas only
  21-triage.md
  22-deep-sent.md
reference/
  postmortems.md        # the "real case" history, keyed by rule id, read on demand
state/
  claims.jsonl          # pre-draft ownership claims (D1) - atomic via git
  threads.jsonl         # per-counterparty nudge counts, draft-created dates, deferral targets
routines/               # backed-up prompts (this dir)
```

Each Routine prompt shrinks to roughly:

> Read `policy/00-invariants.md`, `policy/10-common.md` and `policy/21-triage.md` from
> `shimont/ch-claude-email-routes` and execute your role. If any of those files cannot be read,
> STOP and report — do not improvise from memory. Append this run's claims and thread state to
> `state/` and push.

What that buys:

- **One copy of every rule.** §C1 becomes structurally impossible.
- **A real mutex** (§D1) — git push is atomic, `list_drafts` is not.
- **Cross-run memory.** Nudge counts "per COUNTERPARTY, not per threadId"
  ([`01:607`](routines/01-daily-email.md#L607)) currently has to be re-derived from scratch every
  run by every routine, independently, with no shared answer. A state file makes it a lookup.
- **Incremental scanning.** The deep scan's ~400-thread page-through is the main budget sink; with
  last-seen state it only examines threads that changed. This is the biggest cost win available.
- **Reviewable policy changes** — diffs and history instead of blind in-place prompt edits (§A2).

Two caveats before switching: confirm the Routine environment actually has the repo checked out
with push credentials, and keep the fail-stop above — a routine that can't read its policy must
stop, not fall back on half-remembered rules.

---

## G. Suggested order of work

**Free, do first (deletion and cron edits, no new machinery):**

1. Strip the disowned sections from the deep sent scan (§A1) and fix its self-check 7.
2. Backport the billing-failure protection into deep's noise sweep, or delete that sweep (§C1/§C2).
3. Re-time the crons: deep → `0 21 * * 1,4`, triage → `0 7,11,15,20 * * *` (§D1.1, §D2).
4. Align models — put daily and deep on the same model as triage (§D3).

**Small rule additions, high payoff:**

5. Stale-tag rule, mirroring the stale-draft rule (§B1).
6. Unsent-draft ageing report + never age-out a thread with a pending draft (§B2).
7. Move the terminal/aged-out sweep to daily; widen deep to 35d; use explicit dates (§B3).
8. Add the teammate-outbound sweep (§B4).
9. `FOLLOW-UP-LATER` label for beyond-30-day re-engagement (§B5).
10. Soften the 2-day boundary, or give triage the ≥2d inbound band (§B6).
11. Reconcile by paging, never by `resultCountEstimate` (§B7).

**Structural:**

12. Extract shared policy to this repo; shrink the three prompts to role deltas (§F).
13. Split hard invariants from heuristics; move post-mortems to `reference/` (§E1).
14. Add `state/claims.jsonl` as a real pre-draft mutex (§D1.2).
15. Incremental scanning off `state/threads.jsonl` (§F).

Items 1–4 are edits to existing text and schedules and should take one pass. Items 5–11 are each a
few lines of policy. Item 12 is the one that stops this document from being needed again.
