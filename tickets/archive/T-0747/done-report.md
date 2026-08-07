## Done report

T-0747 (cleanup obligations, child 4 of the T-0739 typestate umbrella):
release-postdominates-acquisition on all exits including exceptional,
escape transfer, per-protocol cleanup policy.

Extended src/frob/gates/_protocol_summary.py's existing per-package scan
(PROTO001-004) with PROTO005, two independent sub-checks sharing the
same package-selection loop (no second repo walk):

1. Resource-level intraprocedural postdominance over the T-0809
   ACQUIRE/RELEASE/ESCAPES DSL: a function that frob:escapes its resource
   transfers the obligation (discharged); one that frob:releases the
   SAME resource itself is trusted at function granularity (the DSL has
   no finer attachment point); otherwise every return (or, with none, one
   implicit fallthrough exit) must be preceded by a same-file call to a
   release-tagged function -- an early return with none is the crisp
   "early-error return skips cleanup" true positive. A
   cleanup="process-exit-ok" policy (looked up from a frob:protocol bound
   to the acquiring symbol or its file) additionally discharges a return
   preceded by a process-terminating call. The exceptional-exit half
   reuses T-0686's frob.arch._mayraise.compute_may_raise directly (no
   second engine) -- Python-only, matching that resolver's own disclosed
   scope -- firing when the function's own may-raise set is non-empty and
   zero release calls appear anywhere in its body (existential,
   false-negative-biased, matching PROTO002/003/004's own disclosed
   approximation posture, not a new one). Language-excuse discharge
   (frob.arch._protocol_excuse, T-0746) is checked first, same as
   PROTO002/003.
2. Protocol-level *_deinit-never-called: a frob:protocol cleanup="always"
   protocol that has been entered (a non-initial state established
   somewhere in the package's closure) but whose terminal state (the
   LAST entry in its declared states= list, by declaration order --
   deliberately not "any state with no outgoing transition", which would
   wrongly call a mid-chain state terminal) is never itself established.
   cleanup="on-error"/"process-exit-ok" protocols are out of this half's
   scope by design (module docstring explains why).

Both sub-checks report rule PROTO005, ERROR by default (matching
PROTO002/003's "enforceable, never fail-silent" mandate), waivable with
frob:waive PROTO005 reason="...".

Registered "PROTO005" in src/frob/gates/__init__.py's _KNOWN_GATE_RULES.
Documented in docs/modules/gates.md (new "PROTO005 (T-0747)" section) and
updated docs/modules/graph.md's resource-tracking-DSL section (which
previously said "real verification is T-0747, not built yet") to point at
the new gate. Scope was extended to include both docs files via
`frob ticket scope --add --reason-file` (same T-0745 precedent: every new
public symbol needs a frob:doc edge resolving to a real anchor).

Changed:
  src/frob/gates/_protocol_summary.py -- new PROTO005 helpers
    (_bare_name, _cleanup_policy, _normalized_module_for, _find_function,
    _acquiring_function_violations, _cleanup_obligation_violations,
    _cleanup_always_violations), _NORMALIZED_ADAPTER_BY_SUFFIX /
    _PROCESS_TERMINATORS constants, _PROTOCOL_TAG_KINDS widened to
    include EdgeKind.ACQUIRE so an acquire-only package still gets
    scanned; wired into protocol_summary_gate's existing per-package loop
  src/frob/gates/__init__.py -- "PROTO005" added to _KNOWN_GATE_RULES
  tests/test_gates.py -- TestCleanupObligationGate (9 tests: true
    positives for the early-return leak, the exceptional-exit leak, and
    deinit-never-called; false-positive-avoidance for escape transfer,
    self-contained acquire+release, release-before-return, the
    python-with discharge, the process-exit-ok policy discharge, and a
    fully-closed cleanup=always protocol chain)
  docs/modules/gates.md -- new "PROTO005 (T-0747)" section
  docs/modules/graph.md -- resource-tracking-DSL section repointed at the
    real verifier
  tickets.md -- T-0747 scope change, evidence, this Done report

Deferred/disclosed, no new ticket needed (already covered by existing
disclosures this ticket inherited): cross-file release resolution (a
RELEASE in a different file is never wired to a bare-name call site this
scan can see -- an explicit frob:escapes is the sanctioned path for that
shape, per this ticket's own module docstring); non-Python exceptional
exits (compute_may_raise is Python-only by its own T-0686 disclosure,
so Rust/TypeScript/Kotlin acquisitions still get the normal-return
postdominance half but not the exceptional-exit half).

Filed T-0923 (out-of-scope discovery, not touched by this
ticket): PROTO004 (T-0840) was never added to _KNOWN_GATE_RULES, so a
frob:waive PROTO004 anywhere in the tree would be flagged WAIVE002 as an
ineffective waiver despite PROTO004 being a real, live gate rule -- the
same listing-omission class T-0753 already fixed once for DEAD001.

Correction to an earlier round of this Done report: this worktree first
saw T-0747's blocker T-0686 (and T-0739's blockers T-0866..69) as
entirely missing from the ledger and filed a "land dropped the block"
bug for it. The coordinator confirmed this was wrong: those tickets were
swept into tickets-archive.md by a TICK003 archive run on main AFTER
this worktree's original warm-up merge, not lost -- this worktree's
ledger simply predated that archive commit. Fixed via `git checkout
main -- tickets.md tickets-archive.md` (both ledger files, matching
playbook 10b) rather than a partial tickets.md-only restore. The
"T-0686 ticket block vanished" bug ticket this session filed earlier is
NOT re-filed here (it does not describe a real bug); only the genuine
PROTO004 registration gap above is kept.

Evidence (bound via --accepts 0, all 9 collected and passing):
  tests/test_gates.py::TestCleanupObligationGate::test_early_return_before_release_call_is_an_error
  tests/test_gates.py::TestCleanupObligationGate::test_release_before_return_is_not_flagged
  tests/test_gates.py::TestCleanupObligationGate::test_escape_transfer_discharges_the_obligation
  tests/test_gates.py::TestCleanupObligationGate::test_self_contained_acquire_and_release_is_trusted
  tests/test_gates.py::TestCleanupObligationGate::test_python_with_block_discharges_the_acquisition
  tests/test_gates.py::TestCleanupObligationGate::test_process_exit_ok_policy_discharges_a_terminator_guarded_return
  tests/test_gates.py::TestCleanupObligationGate::test_exceptional_exit_with_no_release_anywhere_is_an_error
  tests/test_gates.py::TestCleanupObligationGate::test_deinit_never_called_for_cleanup_always_protocol_is_an_error
  tests/test_gates.py::TestCleanupObligationGate::test_deinit_reachable_for_cleanup_always_protocol_is_not_flagged

`uv run pytest tests/test_gates.py -k "TestCleanupObligationGate or Protocol" -q`:
38 passed (9 new + all pre-existing PROTO001-004 suites, all green).
`uv run pytest tests/test_gates.py -q`: full file green.
`uv run frob test --base main`: python selection touched=28 ripple=0,
exit=0, 72.44s.

Gates: `uv run frob check --ticket T-0747` chunked across all 5 stage
groups (lint/static/gates-fast/gates-native/gates-security), measured
against main's ledger post-TICK003-archive (the correct baseline) --
every group PASS, 0 errors. Both PATH ruff and project-pinned
`uv run ruff` clean. No waivers added by this ticket's own new code.

Update (hand-appended, `frob ticket done-report` hung past a 480s retry
budget -- known bug T-0887, using the sanctioned hand-write fallback):
re-merged `main` into this worktree after the above, the code-level
counterpart of the tickets.md/tickets-archive.md ledger sync. Several
sibling tickets (T-0712/T-0879/T-0887 among them) had landed real code
and tests on `main` since this worktree's original warm-up merge that
this worktree's tree did not yet carry, which was producing spurious
COV003/SCOPE001/PRE001 `frob check` findings unrelated to T-0747 (those
gates walk the whole repo/ledger regardless of `--ticket` scoping).
`git merge main` auto-merged cleanly -- tickets.md via the registered
merge driver, `src/frob/gates/__init__.py`'s own PROTO005 registration
untouched, zero conflict markers anywhere. Rebuilt natives (`make core`;
`uv.lock` moved), re-ran `frob ticket sweep T-0747`, and re-verified from
scratch: `git diff main --diff-filter=D --stat` is now EMPTY (the
playbook section 9 deletion-filter check); all 5 `frob check --ticket
T-0747` stage groups (lint/static/gates-fast/gates-native/gates-security)
PASS 0 errors each; `uv run pytest tests/test_gates.py -q` full-file
green; `uv run frob test --base main` python selection touched=28
ripple=0 exit=0 duration=21.18s.

Also corrects an earlier round of this Done report (superseded, not
itself landed as a separate ticket): this worktree initially saw T-0747's
blocker T-0686 (and T-0739's blockers T-0866..69) as entirely missing
from the ledger and filed a "land dropped the block" bug. The coordinator
confirmed this was wrong -- those tickets were swept into
tickets-archive.md by a TICK003 archive run on `main` after this
worktree's original warm-up merge, not lost; this worktree's ledger
simply predated that archive commit. Fixed via `git checkout main --
tickets.md tickets-archive.md` (both ledger files). The incorrect
"T-0686 ticket block vanished" bug ticket this session filed earlier was
NOT re-filed; only the genuine PROTO004-registration-gap discovery
(T-0923) is kept.

Worktree: .claude/worktrees/agent-a51a11716781a450c

### Changed
```
 docs/modules/gates.md               |   68 +
 docs/modules/graph.md               |   18 +-
 src/frob/gates/__init__.py          |    5 +
 src/frob/gates/_protocol_summary.py |  388 ++-
 tests/test_gates.py                 |  248 ++
 tickets-archive.md                  | 6107 ++++++++++++++++++++++++++++++++++-
 tickets.md                          | 5515 +------------------------------
 7 files changed, 6853 insertions(+), 5496 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestCleanupObligationGate::test_early_return_before_release_call_is_an_error` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCleanupObligationGate::test_release_before_return_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCleanupObligationGate::test_escape_transfer_discharges_the_obligation` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCleanupObligationGate::test_self_contained_acquire_and_release_is_trusted` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCleanupObligationGate::test_python_with_block_discharges_the_acquisition` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCleanupObligationGate::test_process_exit_ok_policy_discharges_a_terminator_guarded_return` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCleanupObligationGate::test_exceptional_exit_with_no_release_anywhere_is_an_error` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCleanupObligationGate::test_deinit_never_called_for_cleanup_always_protocol_is_an_error` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCleanupObligationGate::test_deinit_reachable_for_cleanup_always_protocol_is_not_flagged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 9 passed (from 9 evidence id(s))
- gates: 5 error(s), 2323 warning(s), 219 waived
- error-findings: COV003@tickets/T-0650, COV003@tickets/T-0712, COV003@tickets/T-0879, COV003@tickets/T-0887, PRE001@tickets/T-0747
