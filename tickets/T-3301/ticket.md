---
id: T-3301
title: PRE001/TEST006 gate-cache staleness survives sweep; REPLAY annotation may break
  gate-summary parse
state: in-progress
kind: bug
origin: human
created: '2026-08-28'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_verify.py
- src/frob/gates/_gate_cache.py
- src/frob/gates/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_gate_cache.py
  reason: 'reproduced BUG 2 directly (scope --add + sweep, both untracked .frob/ writes,
    then frob check --ticket <id> twice): _replay_fingerprint (this file) folds root_content_key
    (tracked-file content only) + .frob/baseline + build fingerprint, but NEVER the
    per-ticket .frob/prework/<id>.json sweep digest or the gitignored .frob/coverage-stamp
    TEST006 reads -- so a completed sweep/coverage stamp never busts the whole-run
    replay cache for the same --ticket signature, exactly matching F-043/F-048/F-031''s
    reported symptom and remediation (rm -f .frob/gate-cache.db, the file this module
    writes)'
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/gates/__init__.py
  reason: 'F-031: PRE001''s own remediation text (''run: frob ticket start T-0027
    again'') names a verb that then REFUSES (''T-0027 is already in-progress -- run
    sweep instead'') when the ticket is already in-progress, which is always the case
    when PRE001 can fire (prework_gate only runs for IN_PROGRESS tickets); the fix
    (prework_gate/_pre001 in gates/__init__.py) is the same finding this ticket''s
    Done report covers, not a separate scope'
  actor: logan
  at: '2026-08-29'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
REPORTED FROM REAL CONSUMER USE (../diax FROBLEMS.md F-026, F-031, F-043,
F-048). Four reports, and F-043/F-048 explicitly self-identify as "the F-026
family" -- treat as one root-cause investigation with (at least) two distinct
bugs to confirm and fix.

BUG 1 (F-026, precise repro given): a second `frob check` on an unchanged
tree prints a REPLAY-annotated gate-summary line:
    "pass  gate-summary  [REPLAY age=210.5s, unchanged tree]  0 errors, ..."
`frob.app.ticket_runner._verify._GATE_SUMMARY_COUNTS_RE` (confirm exact name
against current main -- this repo has since split _verify.py; there is now a
`_GATE_SUMMARY_COUNTS_ONLY_RE` in src/frob/app/ticket_runner/_verify.py,
worth checking whether it already `.search()`s rather than `.match()`s and
whether it already tolerates the bracketed annotation, since the surrounding
comment references exactly this REPLAY-prefix problem -- this may be PARTLY
OR WHOLLY FIXED already; re-measure before writing any code) expects
`gate-summary\s+(\d+)\s+errors` at a fixed position, so the annotation can
make the self-spawned check report "no parsable gate-summary line", and
`frob ticket close` then refuses with OwnObligationsUnclean even though the
check is genuinely clean.

BUG 2 (F-043, F-048, F-031): a stale `.frob/gate-cache.db` reports phantom
PRE001 ("pre-work sweep is stale") and TEST006 ("coverage stamp is stale")
findings that persist across repeated `frob ticket sweep`/`check` cycles with
NO code or scope change in between, and only `rm -f .frob/gate-cache.db`
clears them -- after which the IDENTICAL command returns exit_code=0. This
means the gate cache is keyed on something a legitimate `scope --add` or
`sweep` rewrite does not invalidate. F-031 additionally reports PRE001's own
remediation text ("run: frob ticket start T-0027 again") naming a verb that
then REFUSES ("T-0027 is already in-progress -- run sweep instead") --
separate from the cache-key bug but worth fixing in the same pass since it is
the same finding's message.

WHAT NOT TO DO: do not fix this by disabling/shortening the gate-cache TTL
across the board -- that would blunt the REPLAY optimization for everyone to
paper over a narrow invalidation bug. Do not fix BUG 1 by loosening the
regex to match ANYTHING that looks like counts either; keep it anchored to
the real gate-summary line shape, just tolerant of the annotation.

WHAT TO BUILD:
  1. Re-measure BUG 1 against current main first -- it may already be fixed
     by the _verify.py split; if so this ticket becomes BUG 2 + the F-031
     message fix only, and should say so in its Done report.
  2. Find what `scope --add` / `sweep` writes that the gate-cache key does
     NOT include (a scope hash? a sweep timestamp?) and add it to the key,
     or invalidate the cache entry on any ledger mutation for the ticket in
     question.
  3. PRE001's remediation text should name `frob ticket sweep <id>` when the
     ticket is already in-progress, matching what `start` itself says on
     refusal, instead of telling the user to run the command that will
     refuse.

MUST-FIRE FIXTURE: an actually-stale pre-work sweep (scope changed, no sweep
run since) must still report PRE001 -- do not over-correct into never firing.

MUST-STAY-QUIET FIXTURE: `scope --add <path>` immediately followed by
`frob ticket sweep <id>` then `frob check --ticket <id>` twice in a row --
zero PRE001/TEST006 findings on either run, and the second run's gate-summary
line (REPLAY-annotated or not) must parse cleanly for `close`/`done-report`.
