---
id: T-4385
title: frob ack rewrites frob.lock unattributed; security.txt Expires timestamp regenerated
  non-deterministically by check -- audit which verbs may write tracked files
state: queued
kind: bug
origin: human
created: '2026-09-09'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ack_runner.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
found while working T-4041.

T-4041 itself (scoped to src/frob/app/verify_runner.py) fixes exactly one instance: frob verify now rewriting frob-coverage.lock.json on the primary with no attribution. Its own body was later amended in place with two more instances of the SAME shape, which are genuinely out of that ticket's declared scope:

F-254 (logand.app-v2, 2026-09-06): frontend/public/.well-known/security.txt's Expires timestamp gets regenerated (non-deterministically -- a fresh timestamp every run) by a static-assets step during check, in a DIFFERENT repo/worktree than this one. Not fixable from src/frob/app/verify_runner.py, and the non-determinism itself means the fix is "stop tracking it or stop regenerating it during a check", not an auto-commit (an auto-commit of a value that changes every run would just create a new commit every run, trading one kind of debt for another).

F-293 (logand.app-v2, 2026-09-06) + the ticket author's own frob ack repro: frob ack rewrites frob.lock and leaves it uncommitted -- costs an implementer a SCOPE001 scope-widen (T-0249/T-0242/T-0248 all paid this tax) and can DirtyMain-block a concurrent land. frob.lock's ownership is unambiguous (frob's own bookkeeping, frob-only format) -- the ticket's own analysis picks fix (1), attribute automatically, same shape T-4041 uses for frob-coverage.lock.json. Lives in whatever module frob ack's CLI wiring is in (not src/frob/app/verify_runner.py) -- needs its own ticket/scope.

Also requested but broader than either individual fix: a stated repo-wide rule for which frob verbs may write tracked files (a reporting verb must not mutate tracked state; anything regenerated belongs in .frob/ or must be committed with attribution by the verb itself), and an audit of every verb against it (ack, verify now, and check's static-assets step are the three known violators so far).

Filed instead of folded into T-4041: different files (frob ack's own module, the static-assets generator, plus whatever survey doc the audit belongs in), all outside src/frob/app/verify_runner.py's declared scope/lease.

ACCEPTANCE
- frob ack accounts for its own frob.lock write (auto-commit with attribution, same shape as T-4041's coverage-lock fix) -- no ticket needs SCOPE001-widen to include frob.lock, no run leaves frob.lock dirty for the next land.
- security.txt's Expires-timestamp regeneration during check addressed on its own terms (stop tracking it, or stop regenerating during check) -- an auto-commit is the WRONG fix here since the content is non-deterministic across runs.
- A stated rule for which frob verbs may write tracked files, with at least ack/verify-now/check's static-assets step audited against it.