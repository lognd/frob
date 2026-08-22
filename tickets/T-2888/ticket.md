---
id: T-2888
title: 'Red-tail sweep round 2: OPAQUE001 fix, LANG004/TICK003/TICK006 characterized'
state: queued
kind: bug
origin: human
created: '2026-08-22'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_refs.py
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
Re-measured 2026-08-22 via unbudgeted `frob check --json` (gate-summary
present): assigned subset is LANG004 (1), OPAQUE001 (1), TICK003 (1),
TICK006 (1). CLAUDE001/TICK004/CYCLE001/DOC006 confirmed out of scope
(coordinator-owned or already-confirmed correctly-left-alone).

## OPAQUE001 (src/frob/gates/_refs.py:31) -- FIXED, narrowly

Root-caused, not guessed: line 31 is inside the module's own docstring
(lines 9-113), textually mentioning `importlib.import_module(...)` as
an EXAMPLE of the opacity concern the gate itself detects -- not a real
call. Reproduced empirically that `_non_executable_byte_spans` fails to
exclude this docstring because a comment block (`frob:waive LARGE001`,
lines 1-8) precedes it: `_PY_DOCSTRING_QUERY_SRC`'s `(module . (string)
@doc)` anchor requires the docstring to be tree-sitter's immediate first
child of `module`, which a preceding comment breaks. Confirmed by
stripping the leading comment from a copy of the file and re-running
the same finder: 0 findings without it, 1 with it.

This is a SHARED-primitive defect (also read by the `sys` scanner per
its own docstring) with candidate wider blast radius (found 3 more
files sharing the vulnerable shape by grep alone: `_config_external.py`,
`check_runner.py`, `config.py`) -- too high-blast-radius to patch in the
same breath as this sweep. Filed T-2885 (investigation-only, no fix
attempted there either) with the full root-cause, reproduction, and a
suggested fix shape for the next agent. Fixed ONLY this one finding here,
narrowly, via an inline `frob:waive OPAQUE001` citing T-2885 -- does not
touch the shared query.

## LANG004 (src/frob/lang/_support.py) -- CHARACTERIZED, not fixed:
execution-context-dependent, not random-flaky

Coordinator asked whether this flaps (environment-dependent) or
regressed. Determined: reliably PASSES via two different direct
in-process reproductions --
`_behavioral_capability_check("strata", "publicness", tmp)` alone, and
the full `capability_conformance_gate(repo_root)` gate function called
directly in a plain script -- both return `[False, True]` (correct) and
zero violations, run twice. Reliably FAILS via the actual `uv run frob
check` CLI pipeline -- twice, including once with `.frob/gate-cache.db`
moved aside to rule out stale-cache replay (T-2723's documented
incident class; ruled OUT, not assumed absent). So this is not random
flapping -- it is a CONSISTENT discrepancy between two invocation paths
of the identical source tree: the real `frob check` CLI vs. a direct
Python import, both via the same `uv run` interpreter/venv.

Strongest lead (not confirmed as the mechanism): a stale globally
`uv tool install`ed `frob` exists at `~/.local/bin/frob` -> `~/.local/
lib/python3.10/site-packages/frob` (pip-reported `Version: 0.0.5`,
predating the `T-2410` clearance-derivation fix entirely -- its
`_walk_strata.py` has no `clearance`/`CAPABILITY_PUBLICNESS` reference
at all). Matches the "Stale global frob" pattern this repo has hit
before. Could NOT trace an actual subprocess call site in the default
(non-`--budget`) check path that would reach this stale install --
`_check_chunking.py`'s budget-chunk path runs `_run_all_stages`
in-process, not via subprocess, so that specific path is ruled out as
the mechanism, but the default unbudgeted path's own gate dispatch was
not fully traced given this ticket's time budget. Recording this as an
accurately-characterized, reproducible, environment-dependent finding
rather than guessing at the exact call site or writing a fix around an
unconfirmed mechanism.

Not fixed, not waived, not filed as a fresh "regression" bug (it isn't
one -- the source is provably correct against direct invocation). If
this recurs, the next investigation should start by tracing whether the
default `frob check` gate-execution path ever resolves `frob`/`python`
via bare `PATH` lookup rather than `sys.executable`/the running venv's
own interpreter, in any of its stages.

## TICK003 (tickets.md, 882 un-archived) -- CORRECTLY LEFT ALONE, same
class as TICK004

Verified against T-2801's own Done report: identical shape already
found and explicitly left unfixed there ("`frob ticket archive` mutates
the whole ledger and this is a live multi-agent session ... Left for a
coordinator-run quiet-moment archive pass"). Re-verified the gate's own
message still says "in a quiet window, no in-flight worktrees" -- not
quiet tonight (multiple concurrent lands observed directly). Not
touched here, matching T-2801's judgment, not overriding it.

## TICK006 (tickets.md: T-2796's Done report claims T-draft-b1ac02d7,
which resolves to nothing) -- CORRECTLY LEFT ALONE, recovered work
already re-filed elsewhere

Investigated whether this is a real, still-open loss or already
resolved. `git log --grep` recovers the original commit (94763205f):
the draft genuinely existed on T-2796's own worktree branch at write
time (a real T-0577 draft-loss-at-land case, not a Done-report typo),
documenting "drop --absorbed-by vs fail" guidance for
docs/guides/agent-playbook.md. Attempting to re-file its content hit
`frob ticket new`'s own 100%-title-match duplicate guard: T-2803
(queued, filed 2026-08-21, same title, same scope
docs/guides/agent-playbook.md) is ALREADY the real successor -- someone
else already performed the recovery. No new ticket needed.

For T-2796's own Done report: NOT hand-edited. Checked established
precedent first (T-2722's Done report, docs/modules/gates.md's own
TICK006 section, archived T-0741): TICK006's Violation carries no
symref (file-scoped to tickets.md only), so a per-instance `frob:waive
TICK006` here would blanket-suppress every current AND future TICK006
finding across the whole ledger -- T-2722 already ruled this out
explicitly for the identical reason, and T-0741 documents ~97 other
pre-existing instances of this exact T-0577 shape, left unwaived and
unbackfilled today because neither available disposition (blanket
waiver, or hand-patching every historical Done report one at a time) is
safe/complete without T-0741's own proposed structural fix (TICK006
symref support, or a documented backfill-note convention). This finding
is one more instance of that ALREADY-TRACKED, ALREADY-ANALYZED debt
class -- correctly left alone, not mechanically waived or hand-patched,
matching the coordinator's stated preference for stating this over
forcing a disposition.

frob:no-behavior-change reason="The only production-code change is one inline frob:waive OPAQUE001 comment naming T-2885 -- no executable behavior changes. LANG004/TICK003/TICK006 are investigation/characterization only, no code touched for any of the three."