---
id: T-2321
title: 'T-2303 child: waive the 3 non-hoistable PERF004/PERF008 sites in _land_cmd.py
  now that T-2314 makes waivers actually work'
state: done
kind: bug
origin: human
created: '2026-08-17'
priority: medium
parent: T-2303
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_land_cmd.py
evidence_scope:
- tests/integration/test_interfaces.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/app/ticket_runner/_land_cmd.py
  reason: 'probe: confirm scope'
  actor: logan
  at: '2026-08-17'
- op: add
  glob: src/frob/app/ticket_runner/_land_cmd.py
  reason: 'probe: confirm scope, no-op since already declared'
  actor: logan
  at: '2026-08-17'
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 9b644c779b13492b0a9f25e6d09a45966a326554
---
Child of T-2303 (parent scope: ARCH001/ARCH103/PERF004/SELFAUDIT001 debt
found by T-2206's sweep). This is the PERF piece.

STATUS: largely already fixed by T-2314 (landed
68b0cdff9466a37a0aa67ddbbac26100940628cb) -- `perf_gate` was reporting
`Violation.file` as an absolute path, so `frob:waive PERF00x` could never
match (`_match_waiver`'s file-level fallback does exact string equality
against a repo-relative waiver src). T-2314 fixed the path shape; measured
116 of 169 raw PERF findings across the repo were being silently unwaived
before that fix.

REMAINING WORK, not covered by T-2314: T-2303's own investigation (before
T-2314 existed) found 3 specific PERF004/PERF008 sites in
`src/frob/app/ticket_runner/_land_cmd.py` that are genuinely NOT hoistable
-- hoisting them would be a correctness regression, not a fix. With T-2314
landed, these can now legitimately be WAIVED instead (previously
impossible). The exact sites and reasoning:

1. `src/frob/app/ticket_runner/_land_cmd.py`, `_python_top_level_defs`
   sort call (was ~line 3494 pre-T-2314, will have moved): `sorted(new_defs
   .items(), key=lambda kv: kv[1])` inside `for rel_path in
   sorted(touched_paths):` -- `new_defs` is recomputed fresh from each
   file's own source two lines above the sort, so this sorts genuinely
   different data on every outer-loop iteration. Nothing invariant to
   hoist.

2. `src/frob/app/ticket_runner/_land_cmd.py`, worktree-porcelain-block scan
   (was ~line 2141): `Path(lines[0][len("worktree ") :]).resolve()` inside
   `for block in spawned.danger_ok.stdout.split("\n\n"):` -- `lines[0]` is
   THIS loop's own per-block porcelain entry (a different worktree path
   each iteration); the one genuinely invariant operand (`resolved`, the
   comparison target) is already computed once, above the loop.

3. `src/frob/app/ticket_runner/_land_cmd.py`, `is_ancestor_of_main`
   retry loop (was ~line 1184): `run_argv(["git", "-C", str(root),
   "merge-base", "--is-ancestor", commit_sha, "main"])` inside `for delay
   in _LAND_PROOF_ANCESTOR_RETRY_DELAYS:` -- the arguments ARE identical
   every iteration, but this is a DELIBERATE retry against changing
   external state (T-1913: suspected commit/ref visibility race -- main's
   ref visibility can genuinely change between retries even with identical
   git args). Hoisting this defeats the retry's entire purpose.

ACTION: add `frob:waive PERF004`/`frob:waive PERF008 reason="..."` at
each of these 3 sites (reasons above, ready to use verbatim) now that
T-2314 makes the waiver actually take effect. Re-measure
`src/frob/app/ticket_runner/_land_cmd.py`'s own PERF floor before/after to
confirm all 3 clear and nothing else regresses. This is now a small,
low-risk, mechanical follow-up (add 3 waiver comments, verify) -- NOT the
land-critical refactor risk T-2303's ARCH child carries.

Scope: src/frob/app/ticket_runner/_land_cmd.py only.