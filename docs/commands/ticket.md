# frob ticket -- CLI surface notes (T-4521)

This page tracks the `frob ticket` subcommand SURFACE (what is a real
verb, what is hidden, what is removed) rather than duplicating the full
behavioral reference already in `docs/modules/tickets*.md`. It exists
because `frob ticket` grew to 53 subverbs (measured 2026-09-16, T-4521's
filing) -- larger than any other verb family in this repo by a wide
margin -- and a chunk of that surface was never meant for a human to
type by hand. See `docs/modules/tickets-lifecycle.md` and
`docs/modules/tickets-landing.md` for the actual mechanics of each verb
below.

## Hidden internal callbacks

Two subcommands are registered exactly like every other verb (fully
dispatchable, same argparse tree) but excluded from `frob ticket --help`
via `argparse.SUPPRESS` -- they are invoked BY other tooling, not typed
by a developer:

- `frob ticket merge-driver %O %A %B` -- the git merge-driver entry
  point git invokes per `.gitattributes`' `merge.frob-ledger.driver`
  registration (`docs/modules/tickets-merge-driver.md`). Still installed
  and invoked exactly as before; only its `--help` visibility changed.
- `frob ticket sweep-async <id> --commit SHA` -- the detached child half
  of `land`'s deferred post-land sweep (T-1684). `land` spawns it; a
  human re-running one by hand (to re-verify a specific commit) still
  can, it just no longer clutters `--help`.

## Removed verbs

These three still parse (so a caller relying on the old spelling gets a
loud, actionable failure instead of "no such command") but their handler
now prints a one-line removal notice naming the replacement and exits 2:

- `frob ticket migrate` -- removed. The one-time v1->v2 ledger migration
  it ran has already been applied everywhere this binary ships. Use
  `frob ticket admin reconcile` to repair a hand-edited/drifted ledger. <!-- frob:waive DOC006 reason="verb introduced by this ticket (T-4521); the resolver runs the pre-land parser" -->
- `frob ticket debt` -- removed. Was a pure alias of the standalone
  `frob debt` (T-1570), which stays the one supported spelling
  (`docs/design/cli-regrouping.md`).
- `frob ticket deprecated` -- removed. Was a pure alias of the
  standalone `frob deprecated` (T-1570); same replacement pattern as
  `debt` above.

## `admin`: disaster-recovery / maintenance verbs

`frob ticket admin <verb>` groups the disaster-recovery-only surface <!-- frob:waive DOC006 reason="verb introduced by this ticket (T-4521); the resolver runs the pre-land parser" -->
under one help heading instead of competing with the everyday queue
verbs:

- `frob ticket admin renumber [old new] [--dry-run]` <!-- frob:waive DOC006 reason="verb introduced by this ticket (T-4521); the resolver runs the pre-land parser" -->
- `frob ticket admin restore <id> --reason TEXT [--no-commit]` <!-- frob:waive DOC006 reason="verb introduced by this ticket (T-4521); the resolver runs the pre-land parser" -->
- `frob ticket admin reconcile [--apply] [--remove-orphans] [--no-commit]` <!-- frob:waive DOC006 reason="verb introduced by this ticket (T-4521); the resolver runs the pre-land parser" -->

Behavior is byte-for-byte identical to the old top-level verbs (same
argument specs, same handlers). The old top-level spellings
(`frob ticket renumber`/`restore`/`reconcile`) still work for one
release -- they are kept as hidden (`--help`-suppressed) aliases, not
removed outright, since these are the disaster-recovery verbs a script
or a muscle-memory habit is most likely to still reach for.

## `points` / `tokens` (T-5132)

`frob ticket points <id> <value>` sizes an existing ticket on the
Fibonacci scale (1 2 3 5 8 13); `frob ticket tokens <id> --tokens-in N
--tokens-out N [--tokens-cache-read N]` manually records measured token
spend. `frob ticket start <id> --unsized-ack REASON` overrides the
points=None start-time refusal. See
`docs/modules/tickets-data-storage.md#points-t-5132` for the full
behavioral reference. <!-- frob:waive DOC006 reason="verbs introduced by T-5132; the resolver runs the pre-land parser" -->

## `sprint migrate` (T-5133)

`frob ticket sprint migrate`: <!-- frob:waive DOC006 reason="verb added by this land; pre-land sweep resolves against the running parser (T-5178)" --> one-shot, idempotent repair moving every
semver-shaped `sprint` label onto `milestone` (normalizing v-prefixed
milestones along the way) and clearing `sprint`. See
`docs/modules/tickets-data-storage.md#sprint-is-a-time-box-milestone-is-the-version-t-5133` for
the full behavioral reference, including the going-forward
`validate_sprint`/`--semver-sprint-ack` refusal that stops the collapse
from recurring. <!-- frob:waive DOC006 reason="verb introduced by T-5133; the resolver runs the pre-land parser" -->

## `runs-last-parallel-safe`

STATUS: NOT YET FOLDED. The plan is `frob ticket runs-last <id>
--parallel-safe (--reason TEXT | --reason-file PATH)` replacing the
standalone `frob ticket runs-last-parallel-safe <id> ...` verb (T-2624);
today both the old standalone verb AND the fold are simultaneously
true/false depending on which lands first -- see T-4521's Done report
for why this one criterion is deferred (a concurrent lease on
`src/frob/app/config.py`, needed for the new `AppConfig` field the flag
requires, blocks it as of this writing). Track the fold separately once
that lease clears.
