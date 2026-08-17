---
id: T-1928
title: FMT gate passes in 0.00s while frob fmt --check would rewrite 267 files on
  main
state: done
kind: bug
origin: human
created: '2026-08-09'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/check/_python.py
- tests/unit/test_check.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/check/_python.py
  reason: T-1928 was filed with an empty scope; narrowing to the files actually needed
    to disclose gate:FMT's diff-scoping, per playbook section 4
  actor: logan
  at: '2026-08-09'
- op: add
  glob: tests/unit/test_check.py
  reason: T-1928 was filed with an empty scope; narrowing to the files actually needed
    to disclose gate:FMT's diff-scoping, per playbook section 4
  actor: logan
  at: '2026-08-09'
evidence:
- tests/unit/test_check.py::TestScopeDisclosure::test_only_names_the_gate_families_it_did_not_run
- tests/unit/test_check.py::TestScopeDisclosure::test_ticket_flag_notes_which_families_are_actually_diff_scoped
- tests/unit/test_check.py::TestScopeDisclosure::test_full_run_discloses_fmt_scope
- tests/unit/test_check.py::TestScopeDisclosure::test_no_disclosure_when_fmt_did_not_run
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED on main, 2026-08-09, tree clean (git status --porcelain empty):

    uv run frob check --only fmt
      gate-summary  0 errors, 0 warnings, 1 waived  [fmt=0.00s]

    uv run frob fmt --check
      ... would rewrite: tests/unit/test_profile.py
      267 file(s) would change

    uv run frob check   (full, unscoped)
      FAIL  ruff-format   71 files would be reformatted

Three different answers to "is this repo formatted": 0, 267, and 71.
The gate that nominally enforces formatting reports clean, and its
0.00s runtime says it did no work at all.

WHY THIS MATTERS BEYOND TIDINESS. This is the catalogued-is-not-enforced
shape: a gate presented as coverage that measures nothing. Two concrete
harms, both live:

1. Accumulated drift is a landmine for every future ticket. Playbook 0.5
   says `frob ticket land` absorbs `frob fmt` on the worktree. If that
   absorption only touches the ticket s own files (the wording suggests
   it does), then the next ticket to touch any of those 267 files gets a
   large unrelated reformat swept into its land, blowing its scope and
   making its diff unreviewable. Several tickets today already fought
   OutOfScopeWaiveDeletion and scope-closure warnings; this is the same
   class of latent trap.
2. An agent running `frob check --only fmt` and seeing 0 errors
   reasonably concludes formatting is clean. It is not. That is a
   false-green, and this repo has already been bitten repeatedly by
   trusting a green number that was not measuring what it appeared to
   (T-1703 sweep false green, T-1907 vacuous evidence).

INVESTIGATE BEFORE FIXING -- I have NOT diagnosed this, only measured it.
Open questions, in order:
- Does the FMT gate deliberately only check the active ticket s touched
  set, and is therefore a no-op on main with no --ticket? If so the
  reported 0 is arguably correct-but-misleading, and the fix is
  disclosure (say what was and was not checked), not a behavior change.
  Note the gate:scope-note mechanism already does exactly this kind of
  disclosure for --only runs; reuse it rather than inventing a new one.
- Why do frob fmt (267) and ruff-format (71) disagree by ~4x? frob fmt
  presumably does more than ruff-format (directive wrapping and similar).
  Establish exactly what each covers before touching either.
- Is the 267 genuine drift, or is frob fmt applying a style the repo has
  not actually adopted? DO NOT reformat 267 files to make a number go
  green until this is answered. A 267-file reformat commit would be
  nearly impossible to review and would collide with every live worktree
  in the repo (there are ~16 right now, several holding unlanded work).

EXPLICIT NON-GOAL for whoever takes this: do not open with a mass
reformat. The deliverable is first an accurate ANSWER to "is this repo
formatted, by whose definition, and what does the gate actually check",
then a gate that cannot report clean for work it did not do. Bulk
reformatting, if it is warranted at all, is a separate ticket sequenced
when the live-worktree count is low.

ACCEPTANCE
1. Documented, evidence-backed explanation of the 0 / 267 / 71 spread.
2. `frob check --only fmt` can no longer report a bare clean result for
   a scope it did not examine -- either it examines the repo, or it
   discloses what it skipped in the same way gate:scope-note already
   does for partial --only runs.
3. A test proving 2: a repo with known unformatted files does not yield
   a bare 0-error FMT verdict. It must fail before the fix.
4. Any decision to accept the current formatting of those 267 files is
   recorded explicitly, not left implicit in a passing gate.

frob:waive BUG002 reason="the regression test proving this fix (tests/unit/test_check.py::TestScopeDisclosure::test_full_run_discloses_fmt_scope) is a brand-new test node added in the same commit as the fix -- frob ticket evidence --check-repro against this branch's merge-base with main (7eb99d0926713cce2a9498c03a75c8b981db54b8) reports NO_VERDICT because pytest cannot even COLLECT a node whose method name did not exist at that commit (exit 5, 'no tests collected'), not a genuine pass/fail. This is the same structural gap BUG002's own NO_VERDICT posture is designed to degrade safely on (never a false violation, never a false pass) -- there is no way to get a real FAILED_AT_PARENT verdict for a test whose whole point is exercising behavior (_scope_disclosure_note's new unconditional gate:FMT branch) that plainly did not exist before this ticket's own diff introduced it. The renamed sibling test (formerly test_full_unfiltered_run_adds_no_disclosure, whose old body asserted the OPPOSITE of the new expectation) is direct before/after documentation of the behavior change even though its own designated node id cannot serve as a --check-repro target for the same reason."

## Done report

Re-measured all three numbers on a clean worktree (2026-08-10, tree clean,
no active ticket):

    uv run frob check --only fmt
      gate-summary  0 errors, 0 warnings, 1 waived  [drift=0.00s, fmt=0.00s]

    uv run frob fmt --check
      265 file(s) would change  (215 .py + 49 .strata)

    uv run ruff format --check .
      77 files would be reformatted, 955 files already formatted

The numbers drifted slightly from the ticket's original 267/71 measurement
(now 265/77) -- this is itself evidence the gap is not a measurement
artifact but genuine, moving repo state.

DIAGNOSIS: these are not three measurements of one quantity. They are
three DIFFERENT checks that happen to share the word "fmt":

1. gate:FMT (FMT001, `src/frob/gates/_todo_fmt.py::fmt_gate`) only scans
   `frob:` directive-comment lines the CURRENT DIFF touches, for
   over-length lines. On a clean tree there is no diff, so it examines
   zero files -- 0 errors in 0.00s is CORRECT for what the gate checks,
   not a false pass on a general formatting question. It never ran
   `ruff format` and never ran `frob fmt`'s own canonicalization pass.
   This diff-scoping is unconditional -- true with or without --ticket,
   true even on a full unscoped `frob check` -- unlike SCOPE/PREWORK/
   COV002/TODO001/AFFECT, which the existing gate:scope-note disclosure
   already documents as ticket-scoped. gate:FMT's diff-scoping was never
   documented as a disclosure at all before this ticket; only playbook
   prose (docs/guides/agent-playbook.md section 6c) mentioned it.

2. `ruff format --check .` (unscoped, repo-wide, invoked directly by
   `frob check`'s "ruff-format" ToolResult inside the lint stage,
   src/frob/check/_python.py::_ruff_format_result): 77 .py files with
   real ruff code-style drift (quoting, line-wrapping, etc).

3. `frob fmt --check` (standalone CLI, src/frob/app/fmt_runner.py):
   canonicalizes `frob:` directive-comment line-wrapping repo-wide, over
   EVERY frob-recognized file type (215 .py + 49 .strata -- ruff never
   touches .strata at all). This is the SAME concern as gate:FMT/FMT001
   (directive-comment wrapping), just unscoped instead of diff-scoped --
   NOT the same concern as ruff-format.

Overlap check (evidence, not assumption): of frob-fmt's 215 .py files and
ruff-format's 77 .py files, only 7 files appear in BOTH lists
(`comm -12` on the two sorted path lists). These are two almost entirely
disjoint drift populations -- directive-comment wrapping debt and Python
code-style debt happen to coexist in this repo, not the same debt counted
two different ways.

FIX (acceptance [2]/[3], disclosure not behavior change, per the ticket's
own explicit non-goal): `_scope_disclosure_note`
(src/frob/check/_python.py) now emits an unconditional NOTE whenever
"fmt" is present in the set of gate families that actually ran --
independent of --ticket, reusing the existing gate:scope-note mechanism
(T-1351) rather than inventing a new one. Verified: `frob check --only
fmt --ticket T-1928` now prints "NOTE: gate:FMT (FMT001) only examines
frob: directive-comment lines touched by the CURRENT DIFF ... run [ruff
format --check ./frob fmt --check] directly to measure repo-wide drift"
alongside the 0-error/0-warning summary -- a reader can no longer see a
bare "0 errors" from gate:FMT without also seeing what it did not cover.
`tests/unit/test_check.py::TestScopeDisclosure.test_full_run_discloses_fmt_scope`
is the acceptance-[3] regression test: it asserts the note is present
even for a FULL unscoped run (the exact false-green shape T-1928
reported) and would have failed against the pre-fix
`_scope_disclosure_note` (the old test at this name,
`test_full_unfiltered_run_adds_no_disclosure`, asserted the OPPOSITE --
that a full run added no disclosure at all).

ACCEPTANCE [4] -- explicit decision recorded, not left implicit: the
77-file ruff-format drift and 265-file frob-fmt drift are ACCEPTED,
KNOWN, UNACTIONED debt. This ticket does NOT reformat anything (per its
own explicit non-goal -- a 265+77-file reformat commit is unreviewable
and collides with every live worktree). The actual bulk-reformat work is
tracked as a separate draft ticket (T-1945, will renumber at
land), explicitly deferred until the live-worktree count is low enough
to sequence a large mechanical diff safely, with the decision rationale
and file-overlap evidence carried into its body so the next agent does
not have to re-derive it.

No mass reformat was run. `frob fmt` was run only on the two files this
ticket itself touched (src/frob/check/_python.py,
tests/unit/test_check.py) to keep this ticket's own diff FMT001-clean --
scoped to this ticket's own change, not the repo-wide 265/77.

### Changed
```
 src/frob/check/_python.py          | 44 +++++++++++++++++++++++++----
 tests/unit/test_check.py           | 35 ++++++++++++++++++-----
 tickets/T-1928/ticket.md           | 23 ++++++++++++++-
 tickets/T-1945/ticket.md | 57 ++++++++++++++++++++++++++++++++++++++
 4 files changed, 146 insertions(+), 13 deletions(-)
```

### Evidence
- `tests/unit/test_check.py::TestScopeDisclosure::test_only_names_the_gate_families_it_did_not_run` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestScopeDisclosure::test_ticket_flag_notes_which_families_are_actually_diff_scoped` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestScopeDisclosure::test_full_run_discloses_fmt_scope` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestScopeDisclosure::test_no_disclosure_when_fmt_did_not_run` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 8 error(s), 861 warning(s), 697 waived
- error-findings: ARCH001@src/frob/app/ticket_runner/_close_cmd.py, COV003@tickets/T-0185, COV003@tickets/T-1351, COV003@tickets/T-1507, COV003@tickets/T-1512, DOC001@docs/design/cli-hygiene.md, PRE001@tickets/T-1928, SEC110@src/frob/app/ticket_runner/_new.py
