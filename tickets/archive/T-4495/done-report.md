## Done report

T-4495 status: READY.

Worktree: /home/logan/projects/frob/.claude/worktrees/t-4495 (branch t-4495)
HEAD: 0e2758e91 "feat(strata): testsuite via-lists ratchet by real site count, not enumeration"

SUMMARY
-------
The previous attempt got blocked before `frob ticket start` because
T-4498 held an in-progress lease on design/frob.strata and the ratchet
lock file. T-4498 landed (state=done) before this attempt started, so
`git -C <WT> merge dev --no-edit` was clean (no conflicts) and `frob
ticket start T-4495` succeeded on the first try -- no LandInProgress
retries were needed for start itself.

WHAT CHANGED
------------
1. design/frob.strata (testsuite node): the four enumerated via-lists
   (env.read ~24 files, exec ~330 files, fs.read ~170 files, fs.write
   ~396 files) are each replaced with a single via "tests/**" glob
   entry. Non-test via-lists on this node (process-control, eval, net,
   net.connect, etc.) and every other node's via-lists are untouched.
   Also added src/frob/strata/_effects.py to stratamod's own fs.write
   via-list (5 -> 6 files) -- the new _write_capability_ratchet_lock_entry
   function is itself a genuine new fs.write site this ticket's own code
   change introduces, so it needed the same real declaration any other
   new write site would.

2. src/frob/strata/_effects.py:
   - _via_is_bare_glob_only(via): true when every via entry has no `::`
     symbol qualifier and contains a wildcard char (*, ?, [).
   - _glob_via_observed_site_count(node, grant, binding, root): counts
     DISTINCT files owned by `node` that match `grant.via`'s glob AND
     carry a real observed effect of the grant's atom kind
     (extract_effects/_line_effects-shaped scan) -- the real measured
     quantity a glob-form via ratchets by, since len(via) would read as
     1 for a single "tests/**" entry.
   - capability_via_site_counts(model, root=None): NEW optional `root`
     parameter. When given, a testsuite-node grant whose via is
     bare-glob-only counts by _glob_via_observed_site_count instead of
     len(via); every other grant, and every call with root=None (every
     pre-existing caller: fix_sys111_capability_ratchet_sync and every
     existing test_effects.py unit test), is byte-for-byte unchanged.
     A bind_code failure logs a warning and falls back to len(via) for
     every grant rather than raising.
   - _testsuite_glob_ratcheted_keys(model): the set of "<node>::<atom>"
     keys eligible for the auto-accept carve-out below -- restricted to
     node.id == "testsuite" specifically (not "any node with a bare-glob
     via"), matching the ticket's "ONLY under testsuite globs" wording.
   - _write_capability_ratchet_lock_entry(root, key, count, reason):
     writes/updates exactly one lock entry in place, preserving every
     other field/entry. Best-effort: read/parse/write failures are
     logged and swallowed, never raised.
   - capability_ratchet_violations(model, root): now calls
     capability_via_site_counts(model, root) (was: model only). When
     observed count > accepted AND the key is testsuite-glob-ratcheted,
     it writes a fresh lock entry with reason "testsuite glob growth"
     and does NOT append a violation -- growth is silently accepted and
     recorded. Every other (node, atom) pair keeps the original
     fail-closed behavior (raises a CapabilityRatchetViolation).
   - Module docstring (the T-1628 ratchet design-rationale comment
     block) and the CAPABILITY_RATCHET_LOCK_REL doc-comment both gained
     a T-4495 section/note disclosing this as the ONE narrow exception
     to "never auto-written by any code path here".

3. docs/design/registry/capability-via-ratchet.lock.json: bumped
   stratamod::fs.write's accepted_count 5 -> 6 with a T-4495 reason
   (the new _effects.py write site). The testsuite::{env.read,exec,
   fs.read,fs.write} entries are left as-is; the FIRST real `frob check`
   run against the new glob vias will auto-write fresh counts for
   whichever of those differ from the current enumerated-era snapshot,
   via the new auto-accept path itself (proven directly by
   test_testsuite_glob_growth_auto_accepts_and_writes_lock).

4. tests/unit/strata/test_selfconform.py: new class
   TestTestsuiteViaGlobRatchet, 4 tests:
   - test_new_test_file_matching_glob_via_needs_no_strata_edit: a new
     tests/**.py file with subprocess + tmp_path writes, against a
     synthetic testsuite node whose ONLY via is "tests/**", produces NO
     SYS_UNDECLARED_INTERFACE violation. (acceptance [1])
   - test_non_test_node_exec_still_fails_closed: a synthetic non-test
     node with NO may "exec" at all still fires SYS_UNDECLARED_INTERFACE
     for a brand-new exec site -- the carve-out never leaks to other
     nodes. (acceptance [2])
   - test_testsuite_glob_growth_auto_accepts_and_writes_lock: a
     testsuite node with a bare "tests/**" exec via, no lock entry,
     growing to 1 real site -> capability_ratchet_violations returns ()
     and the lock file is written with accepted_count=1, reason
     "testsuite glob growth". (acceptance [3])
   - test_non_testsuite_bare_glob_via_is_not_auto_accepted: the SAME
     bare-glob-via shape on a non-testsuite node still raises a real
     CapabilityRatchetViolation and writes nothing -- proves the
     carve-out is testsuite-specific, not "any glob-form via". (acceptance
     [3])

   NOTE on a mechanical mistake caught and fixed during this session: my
   first Edit call matched the tail of test_unexpired_waiver_still_
   visible_in_floor_view's assertion block without noticing that test
   had one more assert line after the block I matched (I had read the
   file with an offset/limit that stopped one line short of the true
   EOF). This split that pre-existing test across my insertion. Caught
   by ruff (F821 undefined name `result`) before running anything;
   fixed by moving the orphaned assert back into its original test and
   removing the duplicate. Re-ran ruff/format clean afterward.

DID NOT TOUCH (disclosed, not silently dropped)
-------------------------------------------------
docs/strata/surface.md documents this exact convention (the "Capability
via-list one-way ratchet" section, ~line 418, and the T-2502 fragments
section's "every ticket that adds a test file appends another glob to
the testsuite node's via lists" paragraph, ~line 948) and per the
ticket instructions should have been updated in the same change.
`frob ticket scope T-4495 --add docs/strata/surface.md` was refused:
ScopeLeaseConflict -- the whole file is already leased by T-4512 (an
unrelated in-progress Unity .asmdef ticket that happens to declare this
whole file in its own scope), and a `frob ticket land` process for
T-4512 was running at the time (pid 986197), which also blocked the
worktree-local scope edit from mirroring to main on the first attempt
(retried and it mirrored fine as a worktree-local change, but the ADD
itself was refused outright by the lease collision, not just the
mirror). Per the brief's hard rule ("a lease refusal naming another
ticket means stop and report, never --steal"), left untouched. Filed:
none new -- recommend the coordinator either fold this doc update into
T-4512's own land (unlikely, unrelated topic) or open a small follow-up
ticket once T-4512's lease clears.

PRE-EXISTING, UNRELATED TEST FAILURE (not caused by this change)
------------------------------------------------------------------
tests/unit/strata/test_selfconform.py::TestExtendedKindsDriftLock::
test_extended_kinds_is_disjoint_from_kind_map fails on this worktree's
dev-merged base: `_EXTENDED_KINDS | _KIND_MAP.keys()` is missing 'net'
relative to `frob.vet._capability._PATTERNS`'s current kind space.
Confirmed pre-existing and unrelated to T-4495: the failing assertion's
three inputs (_EXTENDED_KINDS from _selfconform.py, _KIND_MAP from
_effects.py, _PATTERNS from vet._capability) are all either files this
ticket never touches (_selfconform.py, vet/_capability.py) or, for
_KIND_MAP, a dict this ticket's diff never edits a single line of.
`git log --oneline -3 -- src/frob/vet/_capability.py` shows the most
recent change is T-4536 "Wire a C# capability resolver into
_capability_scan.py" (landed on dev before this worktree's merge),
which is the far more likely source of a newly-appeared 'net' pattern
kind. Not fixed here (out of scope); flagging for the coordinator to
file if not already tracked.

VERIFICATION (this session, verbatim tails)
--------------------------------------------
ruff check src/frob/strata/_effects.py tests/unit/strata/test_selfconform.py
  -> All checks passed!
ruff format --check (same two files)
  -> 2 files already formatted
ty check src/frob/strata/_effects.py
  -> All checks passed!
pytest -p no:xdist tests/unit/strata/test_selfconform.py tests/unit/strata/test_effects.py
  -> SUITE-RESULT: exitstatus=1 collected=135 failed=1
     (the ONE failure is the pre-existing, unrelated T-4536-caused
     TestExtendedKindsDriftLock failure documented above; re-ran after
     the final commit, same single failure, confirmed stable)
pytest -p no:xdist tests/unit/strata/test_selfconform.py::TestTestsuiteViaGlobRatchet
  -> SUITE-RESULT: exitstatus=0 collected=4 failed=0
pytest -p no:xdist tests/gates_suite/test_sys.py tests/gates_suite/test_fix_engine.py
  -> SUITE-RESULT: exitstatus=0 collected=148 failed=0
design/frob.strata parses cleanly: load_design_ids(root, "design").errors == ()

git -C <WT> status --short: empty (everything committed, HEAD 0e2758e91)

ACCEPTANCE CRITERIA (bound, worktree-local ledger, mirrored)
--------------------------------------------------------------
[1] bound: TestTestsuiteViaGlobRatchet::test_new_test_file_matching_glob_via_needs_no_strata_edit
[2] bound: TestTestsuiteViaGlobRatchet::test_non_test_node_exec_still_fails_closed
[3] (new free-text criterion, registered this session) bound:
    TestTestsuiteViaGlobRatchet::test_testsuite_glob_growth_auto_accepts_and_writes_lock

Per the brief, no ticket-scoped `frob check` and no `frob ticket
done-report` were run in this session (instructed skip) -- ruff/ty/
serial pytest above are the verification substitute.

Not landed, per instructions.

### Changed
```
 design/frob.strata                                 | 100 +++++----
 .../registry/capability-via-ratchet.lock.json      |   6 +-
 src/frob/strata/_effects.py                        | 228 ++++++++++++++++++++-
 tests/unit/strata/test_selfconform.py              | 145 +++++++++++++
 tickets/T-4495/ticket.md                           |  31 ++-
 5 files changed, 441 insertions(+), 69 deletions(-)
```

### Evidence
- `tests/unit/strata/test_selfconform.py::TestTestsuiteViaGlobRatchet::test_new_test_file_matching_glob_via_needs_no_strata_edit` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestTestsuiteViaGlobRatchet::test_non_test_node_exec_still_fails_closed` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestTestsuiteViaGlobRatchet::test_testsuite_glob_growth_auto_accepts_and_writes_lock` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
