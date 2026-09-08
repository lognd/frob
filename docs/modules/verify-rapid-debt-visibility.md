# frob.app.verify_runner -- rapid-debt visibility (T-4324)

<!-- frob:describes src/frob/app/verify_runner.py::RapidDebtEntryView -->

`frob verify status` (`src/frob/app/verify_runner.py`) surfaces LIVE
`.frob/rapid-debt.jsonl` `post-land-unscoped-sweep-deferred` entries
(T-1681/T-1684) as part of its `VerifyStatus` payload -- this is a small,
self-contained doc for the ONE new public symbol that fix introduced
(`RapidDebtEntryView`), split out as its own file rather than added to
`docs/modules/tickets-verify-sweep.md` so this ticket's scope stays the
narrow file it was filed against: that doc's existing anchors already
reach dozens of unrelated symbols across the tickets/verify subsystem
(the merge queue, quarantine, watermark, ...), and folding a new anchor
into it would pull all of that into T-4324's scope-closure obligations
for a one-symbol addition.

MEASURED (2026-09-08): five commits (T-4197, T-4301, T-4305, T-4306,
T-4307) sat in `.frob/rapid-debt.jsonl` as
`skipped: post-land-unscoped-sweep-deferred`, sitting uncleared and
unpromoted at filing time, while `frob verify status` reported
`unverified depth: 0` and `quarantine: clear` -- every status surface
read clean despite five factually-unverified commits. `RapidDebtEntryView`
is the view model `VerifyStatus.rapid_debt_live` (a new field on the
existing `VerifyStatus` payload, see
`docs/modules/tickets-verify-sweep.md#frob-verify-cli-t-1697` for that
payload's own pre-existing doc) is built from.

## Liveness

<!-- frob:invariant INV-052 -->

`.frob/rapid-debt.jsonl` is a permanent append-only audit log (T-2997) --
an entry is never rewritten or deleted, so "live" is computed rather than
stored (`_live_deferred_sweep_debt`): an entry is CLEARED once the rolling
post-land-sweep baseline (`.frob/rapid-sweep-baseline.json`,
`src/frob/app/ticket_runner/_rapid_sweep.py`'s own `_BASELINE_REL`) has
since been written at a commit that is the debt entry's commit or one of
its git descendants -- that later sweep necessarily measured this
commit's changes too, even though its own dedicated deferred sweep never
ran or reported UNMEASURABLE. No baseline at all, or a baseline that has
not yet advanced past the debt commit, leaves the entry LIVE
("unmeasured is not zero", the same posture this file's neighbor,
`frob.verify._worker`'s T-3464 `_vanished_pairs_appended_since`, uses for
the identical log).

## Where it surfaces

- `frob verify status` (human): a `rapid-debt (deferred sweep,
  unverified): <n>` line, one entry per line, when non-empty; `clear`
  otherwise -- and the command now exits non-zero while any entry is
  live, the same porcelain rule quarantine already had.
- `frob verify status --json`: `VerifyStatus.rapid_debt_live`, an array
  of `{commit, ticket_id}` objects (`RapidDebtEntryView`), empty (never
  `null`) when clear.
