---
id: T-1351
title: Scope-filtered check output must disclose what it suppressed (T-1293 false-close
  guard)
state: done
kind: bug
origin: agent
created: '2026-07-31'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/check/**
- docs/guides/agent-playbook.md
- tests/unit/test_check.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_check.py
  reason: 'The scope-note fix''s own regression tests live in tests/unit/test_check.py

    (the existing home for _run_gates/_gates_success_result unit tests, per

    the file''s own established precedent for this exact function family).

    Needed for COV002 (frob:ticket edge) and SCOPE001 (declared scope) to

    pass on the code these tests actually cover.

    '
  actor: logan
  at: '2026-07-31'
evidence:
- tests/unit/test_check.py::TestScopeDisclosure::test_only_names_the_gate_families_it_did_not_run
- tests/unit/test_check.py::TestScopeDisclosure::test_ticket_flag_notes_which_families_are_actually_diff_scoped
- tests/unit/test_check.py::TestScopeDisclosure::test_no_disclosure_when_fmt_did_not_run
designated_repro_test: null
acceptance:
- text: given frob check --ticket T-XXXX, when it reports a gate as clean, then the
    output states that the run was scope-filtered and how many findings were suppressed
    outside that scope
  evidence:
  - tests/unit/test_check.py::TestScopeDisclosure::test_only_names_the_gate_families_it_did_not_run
  - tests/unit/test_check.py::TestScopeDisclosure::test_ticket_flag_notes_which_families_are_actually_diff_scoped
  - tests/unit/test_check.py::TestScopeDisclosure::test_no_disclosure_when_fmt_did_not_run
evidence_changes:
- old_node: tests/unit/test_check.py::TestScopeDisclosure::test_full_unfiltered_run_adds_no_disclosure
  new_node: tests/unit/test_check.py::TestScopeDisclosure::test_no_disclosure_when_fmt_did_not_run
  reason: 'The old node test_full_unfiltered_run_adds_no_disclosure asserted that
    a

    full unfiltered run adds NO disclosure at all -- T-1928 (e68f129b115f)

    deliberately overturned exactly that: gate:FMT is diff-scoped by

    construction, so even a full unscoped run must now disclose it, and the

    test was renamed/rewritten to assert the opposite

    (test_full_run_discloses_fmt_scope). T-1351''s literal acceptance-[0]

    claim ("full unfiltered run adds no disclosure") is genuinely obsolete,

    not restorable. Re-pointing to test_no_disclosure_when_fmt_did_not_run

    instead, which proves the part of T-1351''s original intent that is still

    true today: the disclosure note stays silent when nothing actually

    applies (no --only narrowing, no --ticket, and the fmt family itself did

    not run) -- i.e. the note is not spuriously noisy. This is a narrower,

    honest claim, not the original one; recorded here rather than silently

    implied unchanged.

    '
  actor: logan
  at: '2026-08-10'
threat: null
component: check
anchor: false
anchor_reason: null
---
Filed 2026-07-31 as the GUARD for the T-1293 false-close (see the perf burn-down successor). An audit finding gets two tickets: the fix, and the thing that would have caught it. This is the latter.

THE DEFECT: "frob check --only test --ticket T-XXXX" filters findings to the ticket's declared scope. An agent that runs it and sees "0 findings" reasonably concludes its package is clean. It is not -- the scope is typically much narrower than the package, and the unscoped gate may still show dozens of findings. On T-1293 this produced a confidently-reported false green that survived land AND close, and was caught only by an out-of-band coordinator re-measure.

This is the "catalogued is not enforced" failure mode in a new place: a completion claim backed by a number that does not mean what the reader thinks it means.

PROPOSALS (pick per implementation reality, do not assume):
1. When a check run is scope-filtered by --ticket, SAY SO in the output and in the summary line -- e.g. "gate:TEST 0 errors (FILTERED to T-1293's scope; 65 findings exist outside it)". The suppressed count is the load-bearing number and is currently invisible. This alone would have prevented the incident.
2. Make TEST005's own finding text name the measurement command that produces the number the gate reads, so an agent cannot substitute a scoped pytest --cov run by accident.
3. Consider whether a coverage-derived gate should refuse to report at all when the coverage stamp is stale or absent, rather than silently reporting against old data.
4. Document the measurement protocol in docs/guides/agent-playbook.md: how to measure a coverage-gated burn-down, and that a --ticket-scoped zero is not a package zero.

BLOCKER ASSESSMENT: T-1335 is already open on "make coverage" (stamp failure not propagated, stale fixture paths break coverage xml). If the repo-wide coverage stamp is unreliable or unrefreshable by a worktree agent, then EVERY TEST005 burn-down ticket is unverifiable by the agent working it -- which makes T-1335 a blocker for the entire burn-down campaign rather than a side issue. Assess this and, if confirmed, record the dependency explicitly.

## Done report

Implemented per the ticket's own instruction to "pick per implementation
reality, do not assume" -- investigated first and the literal premise
("--ticket filters findings to the ticket's declared scope") does not
hold for most gate families. Verified directly (frob check --only test,
with and without --ticket, --json diff): gate:TEST and gate:COV's COV001
report the EXACT SAME repo-wide counts in both cases (482/22 identical).
Only gate:SCOPE/gate:PREWORK and the diff-driven checks folded into
gate:COV (COV002/TODO001) and gate:FMT/gate:AFFECT are actually scoped to
the ticket's touched set. The real mechanism behind the T-1293 incident
is therefore the OPPOSITE of the ticket's literal wording: a repo-wide
"0 findings" was misread as ticket-scoped-and-clean, not a genuinely
filtered number hiding real findings. The second cited instance (T-1337,
--only opaque --ticket T-1337 never surfacing new INV006 errors) is a
distinct, simpler mechanism: `--only <subset>` runs ONLY the named gate
families, so anything outside it is invisible by construction, unrelated
to --ticket at all.

Fix implemented in src/frob/check/_python.py:
- New `_scope_disclosure_note(*, ticket, gates, ran)` (pure function):
  returns a disclosure string whenever `--only` narrowed the gate
  selection below the full `_ALL_GATES` set (naming every family NOT
  run this invocation -- addresses the T-1337 instance) and/or whenever
  `--ticket` is set (clarifying which families ARE actually diff/ticket-
  scoped vs which are repo-wide -- addresses the T-1293 instance,
  correctly, per what --ticket actually does).
- `_gates_success_result` now threads `ticket`/`gates` through and
  appends a `gate:scope-note` `ToolResult` (warn-severity, never
  blocking) whenever the note is non-None, right before the existing
  `gate-summary` line.
- Manually verified against the real T-1337 shape: `frob check --only
  opaque --ticket T-1351` now prints "NOTE: --only ran 2/38 gate
  famil(ies); NOT run this invocation (status unknown, not clean): ...
  invariant, ..." plus the --ticket clarification note, exactly the
  disclosure that would have caught T-1337 before it landed.

docs/guides/agent-playbook.md: new section 6c documents the measurement
protocol (proposal 4) -- cites both T-1293 and T-1337 as the concrete
incidents, states plainly that --ticket does NOT filter most gate
families (with the specific list of what it does scope), and folds in
the TEST005-specific guidance (a locally-scoped `pytest --cov` run
structurally cannot produce a trustworthy TEST005 count for files it
never measured, per `_test005_symbols`'s own skip-when-unmeasured
design) -- this connects directly to T-1335's coverage-pipeline work
from the same dispatch.

Not implemented (disclosed, not silently dropped): proposal 2 (naming
the measurement command inside TEST005's own finding text) and proposal
3 (a coverage-derived gate refusing to report at all on a stale/absent
stamp) -- both are real, separately-scoped improvements to
src/frob/gates/_coverage.py, which T-1335's own residue ticket (its
Done report's "T-1335 residue" ticket, scoped to that exact file) is the
right home for; folding them into this ticket's src/frob/check/**-only
scope would have meant editing a file outside it.

Also fixed in this dispatch, as its own small ticket (T-1362, landed
separately): a `ty` no-matching-overload regression T-1335's own new
test (tests/unit/test_makefile_coverage.py) introduced, found while
verifying this ticket's lint stage.

Verification: `uv run pytest tests/unit/test_check.py -p no:cacheprovider
-q` (full file, all pass) and `tests/system/test_cli_check.py` (full
file, all pass, confirming no ToolResult-shape assumption elsewhere in
the test suite broke from the new `gate:scope-note` stage). `frob check
--ticket T-1351 --only coverage --only scope --only invariant --only
tickets` shows only pre-existing, unrelated errors (2x INV006 in
src/frob/app/** -- explicitly leased/excluded from this dispatch's scope
-- and 1x TICK003 ledger-archive threshold), confirmed by diffing against
the identical error set observed before this ticket's changes.

Land-mechanics note for this Done report's own honesty: this ticket's
code (src/frob/check/_python.py, tests/unit/test_check.py, docs/guides/
agent-playbook.md) was swept onto main incidentally by T-1362's own land
(the wip-commit step picks up ALL uncommitted worktree changes, not just
the ticket being landed) before this ticket's own scope/evidence/Done-
report cycle ran -- confirmed via `git log`/file diff on main matching
this worktree exactly. This Done report and the scope/evidence CLI calls
above were re-applied against main's current ledger state after that
fact, so `frob ticket land T-1351` below is a ledger-only land (the code
diff versus main is empty; only tickets.md's own state transition needs
to land).

### Changed
```
 tickets.md | 27 +++++++++++++++++++++++++--
 1 file changed, 25 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/unit/test_check.py::TestScopeDisclosure::test_only_names_the_gate_families_it_did_not_run` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestScopeDisclosure::test_ticket_flag_notes_which_families_are_actually_diff_scoped` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestScopeDisclosure::test_full_unfiltered_run_adds_no_disclosure` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 2 error(s), 920 warning(s), 688 waived
- error-findings: PII012@tests/unit/test_doctor_runner_t1276.py, TICK003@tickets.md
