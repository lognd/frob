## Done report

REWORKED after reviewer REJECT #1: the initial `>` (increase-only) count
comparison had a masking gap the reviewer correctly flagged -- a land
whose own diff introduces N new errors could still sail through whenever
an UNRELATED fix on the same branch removed more than N (a self-introduced
regression laundered by a net-better scope-wide total). Took the
reviewer's preferred route (option 2): narrowed the comparison to be
diff-scoped via finding IDENTITY (rule id + file) rather than accepting
the count-only risk.

What changed on top of the original `>` fix:
- `DoneReportClaims` (src/frob/tickets/_models.py) gained an optional
  `error_findings: frozenset[tuple[str, str]] | None` field alongside the
  existing `gate_errors` count -- `None` means no identity capture was
  supplied (old Done reports, or a caller that only ever wired
  `check_gates`); a real (possibly empty) frozenset means the identity
  comparison is authoritative. `render_claims_block`/
  `parse_claims_from_done_report` round-trip it via a new
  `- error-findings: RULE@file, ...` line (or the
  `- error-findings: none (measured, zero errors)` marker for a measured-
  empty set, distinct from the line being absent -- mirrors T-0832's
  measured-vs-unmeasured precedent for `gate_errors` itself).
- `set_done_report` (src/frob/tickets/__init__.py) gained an optional
  `check_gate_findings` parameter, captured into `claims.error_findings`
  alongside the existing `check_gates` count capture.
- `_reverify_done_report_claims_post_merge`/`_land_locked`/`land`
  (src/frob/tickets/_land.py) gained the same optional
  `check_gate_findings` parameter. When BOTH the captured claim
  (`claims.error_findings`) and a fresh `check_gate_findings()` call carry
  a real frozenset, the comparison is now: take
  `fresh_findings - claims.error_findings` (genuinely NEW findings since
  the claim was captured), filter to only those whose file matches
  `ticket.scope` (the diff-touched-files PROXY available in this module --
  `frob.tickets` deliberately has no `frob.gitio`/`frob.gates` diff-
  computation access, docs/rework.md cycle-avoidance), and refuse iff any
  remain. A new error OUTSIDE the ticket's own scope does not refuse here
  (it is some other ticket's own responsibility to catch at ITS land).
  Either side missing an identity set falls through UNCHANGED to the
  original count-only `>` comparison -- strictly additive, never a
  behavior change for a claim that never captured identities.
- `src/frob/app/ticket_runner.py` gained `_check_gate_findings_fn` (a new
  CLI closure, sibling to the existing `_check_gates_summary_fn`) that
  spawns a fresh `frob check --ticket` and parses every `## Errors`
  diagnostic line's `(rule_id, file)` pair. Wired into both `_land`'s and
  `_done_report`'s `set_done_report`/`land` calls. Scope widened +1 for
  this file (see below) -- the reviewer's own reject note sanctioned
  widening here ("if the capture write lives outside scope, widen with an
  honest reason") since the real identity data can only come from
  `frob check`'s own printed findings, which this module already spawns
  and parses for the sibling count-only closure.

Known, accepted cost (not silently dropped): `_check_gate_findings_fn`
spawns its OWN `frob check --ticket` subprocess, independent of
`_check_gates_summary_fn`'s -- when both are wired to the same land/
done-report call (the real CLI path), that is a SECOND full check run.
Deduplicating the two into one shared subprocess result is a real,
worthwhile follow-up, not implemented in this pass (correctness-first);
noted in `_check_gate_findings_fn`'s own docstring and left as a TODO for
whoever picks up the WAIVE004 follow-up ticket next (see below).

Remaining gap, explicitly accepted: the identity comparison above does
NOT yet exclude findings whose rule self-declares scoped-run flakiness
(WAIVE004's "known-flaky for diff-scoped rules ... trust this only from a
full, unscoped run" caveat) -- a flaky WAIVE004 finding that newly appears
in a diff-touched file between done-report time and land time still
counts as a "new in-scope finding" and refuses. This is a narrower version
of the SAME risk class the original ticket named, now scoped down to just
the WAIVE004 half (the count-vs-identity masking half the reviewer flagged
is now closed). Left as a follow-up rather than solved here because
excluding WAIVE004-flagged rules needs cross-referencing against
`frob.gates`'s own WAIVE004 detection at comparison time, which is a
larger, separable piece of work. T-0850 (filed under the
original T-0846 pass) already tracks this; its scope
(`src/frob/gates/**`, `src/frob/check.py`, `src/frob/app/ticket_runner.py`,
`src/frob/tickets/_land.py`) already covers what remains, so it was not
re-filed or re-scoped -- its premise ("closing this needs check_gates to
expose per-finding identity") is now partially satisfied by this pass; the
remaining, narrower piece is the WAIVE004 filter specifically plus
deduplicating the two check_gates*/check_gate_findings subprocess spawns.

Scope widened over this rework: +1 `src/frob/app/ticket_runner.py` (the
real `check_gate_findings` closure), +1
`tests/test_ticket_done_report_claims.py` (round-trip coverage for the new
`error_findings` field) -- both via `frob ticket scope T-0846 --add` with
an honest reason, on top of the `tests/test_ticket_land.py` widening from
the original pass.

New adversarial test:
`tests/test_ticket_land.py::TestClaimDivergencePostMerge::test_masked_self_introduced_error_in_own_scope_still_refuses_via_identity`
-- captured claim: 2 errors, identities {RULE_A@src/other.py,
RULE_B@src/other.py}; fresh post-merge: 1 error total (a net DECREASE, so
the count-only `>` fallback alone would pass this land) but the one
surviving finding is a brand-new RULE_C@src/feature.py inside the ticket's
own `src/**` scope and absent from the captured claim -- must REFUSE. This
fails against a count-only `>` comparison (1 > 2 is False, would
incorrectly pass) and passes only when the identity/scope comparison is
wired, exactly the masking scenario the reviewer named. All prior boundary
tests (lower/equal/higher count, unmeasured-gates, no-claims-section)
re-verified still green with no changes needed to them.

Verification: `uv run pytest tests/test_ticket_land.py -k
ClaimDivergence -q` (9 passed), `uv run pytest
tests/test_ticket_done_report_claims.py -q` (10 passed, including the two
new error_findings round-trip tests),
`tests/test_ticket_land.py::TestDoneReportThenLandRealClosuresEndToEnd`
(the real-CLI-closures end-to-end test, still passing with the new
`_check_gate_findings_fn` closure wired in). `uv run ruff check`/`ruff
format` clean on every touched file. `uv run ty check` clean on every
touched file. `uv run frob check --ticket T-0846` clean across all five
--only stage groups (lint, static, gates-fast, gates-native,
gates-security) after a `frob ticket sweep T-0846` refresh following the
scope changes.

ROUND 2 (TEST016 land refusal + T-0441 catch-22, same worktree, after
coordinator merged main and refreshed the post-merge capture):

TEST016 refused land: `_check_gate_findings_fn`'s changed lines in
`src/frob/app/ticket_runner.py` had zero bound evidence, so 4 mutants
survived (two `capture_output=True`/`text=True` bool negations, one
`check=False` bool negation, one `len(section) < 2` operand swap). Added
`tests/unit/test_ticket_runner_gate_findings.py` (scope widened +1, honest
reason), following `tests/unit/test_ticket_runner_land_release.py`'s
existing precedent: monkeypatch `frob.process._guard.subprocess.run`
directly rather than spawning a real `frob check`. Five new tests: a
happy-path multi-finding parse, a refused-spawn-returns-None kill-switch
proof (mirrors `TestLandRebuildNativesFn`'s T-0803 spy pattern), an
unparsable-output-returns-None case, a `len(section) < 2` BOUNDARY pin
(crafted output with NO `## Errors` heading but a parsable, zero-error
gate-summary -- the length-1 case just below the `< 2` cutoff -- which an
operand-swapped mutant crashes on with `IndexError` since it would then
try `section[1]` on a length-1 list), and a kwargs-capture test asserting
the literal `capture_output`/`text`/`check` values `subprocess.run`
actually received. Verified BY HAND: reverted each of the 4 fixed lines
back to its mutant form one at a time and confirmed the corresponding new
test fails (capture_output->False and text->False and check->True each
fail the kwargs-capture test; the `<` swap fails both the boundary test
and the unparsable-output test with an uncaught IndexError) -- same
methodology as the original masking test's hand-verification.

Second item, same round: a deterministic land failure on T-0441 (a ticket
adding a `frob fmt` subcommand) surfaced the SAME "capture vs fresh-check
run-context divergence" class this ticket is about, one level down:
`_check_gates_summary_fn`/`_check_gate_findings_fn` both spawned
`sys.executable -m frob check` -- whatever interpreter the CALLING process
runs under, not the tree being checked. `done-report` capture runs from
inside the worktree (worktree venv, worktree's own editable install);
`land` runs from the root checkout (root venv, main's code) but re-checks
the post-merge WORKTREE tree. For a ticket that adds/removes a public
surface a gate validates against the LIVE running registry, the root-venv
process's own `frob` package has no knowledge of the worktree's new
surface, so a gate like DOC005 (cross-checking README subcommand rows
against the live `_build_parser` registry) deterministically errors
post-merge on rows the capture legitimately saw as fine -- refresh-and-
retry can never converge because the two runs check two DIFFERENT
installed trees' code, not two views of the same one.

Fix: added `_python_for_tree(root)` (`src/frob/app/ticket_runner.py`) --
`root/.venv/bin/python` when it exists, else `sys.executable` as a
fallback (never a hard error, strictly a refinement over the prior
unconditional `sys.executable`). Wired into both closures' spawn argv.
Four new tests in the same test file (`TestPythonForTree`): tree-venv-
present resolves to that path, tree-venv-absent falls back to
`sys.executable`, and one end-to-end argv-capture test per closure proving
the SPAWNED argv actually uses the tree-local interpreter. Verified BY
HAND: reverted `_python_for_tree(root)` back to `sys.executable` at both
call sites and confirmed both new argv-capture tests fail (comparing the
worktree's own `.venv/bin/python` against pytest's `tmp_path`-local
fake venv path, which can never match the real running interpreter).

Verification (round 2): `uv run pytest
tests/unit/test_ticket_runner_gate_findings.py -q` (9 passed). `uv run
pytest tests/unit/test_ticket_runner_gate_findings.py
tests/test_ticket_land.py tests/test_ticket_done_report_claims.py
tests/unit/test_ticket_runner_land_release.py -q` (129 passed, no
regressions). `uv run ruff check`/`ruff format` clean. `uv run ty check`
clean. `uv run frob check --ticket T-0846` clean across all five --only
stage groups after a `frob ticket sweep T-0846` refresh.

### Changed
```
 src/frob/app/ticket_runner.py           |  91 ++++++++
 src/frob/tickets/__init__.py            |  21 ++
 src/frob/tickets/_land.py               | 144 ++++++++++++-
 src/frob/tickets/_models.py             |  78 ++++++-
 tests/test_ticket_done_report_claims.py |  50 +++++
 tests/test_ticket_land.py               | 104 +++++++++-
 tickets.md                              | 356 +++++++++++++++++++++++++++++++-
 7 files changed, 829 insertions(+), 15 deletions(-)
```

### Evidence
- `tests/test_ticket_land.py::TestClaimDivergencePostMerge::test_lower_gate_error_count_than_claim_still_lands` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestClaimDivergencePostMerge::test_masked_self_introduced_error_in_own_scope_still_refuses_via_identity` (pytest node id, verified passing when recorded)
- `tests/test_ticket_done_report_claims.py::TestDoneReportClaimsModel::test_error_findings_round_trips_through_a_done_report_body` (pytest node id, verified passing when recorded)
- `tests/test_ticket_done_report_claims.py::TestDoneReportClaimsModel::test_measured_empty_error_findings_differs_from_none` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_gate_findings.py::TestCheckGateFindingsFn::test_parses_multiple_findings_from_errors_section` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_gate_findings.py::TestCheckGateFindingsFn::test_refused_spawn_returns_none_not_empty_set` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_gate_findings.py::TestCheckGateFindingsFn::test_unparsable_output_returns_none` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_gate_findings.py::TestCheckGateFindingsFn::test_no_errors_heading_with_parsable_summary_is_measured_empty` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_gate_findings.py::TestCheckGateFindingsFn::test_spawn_kwargs_capture_output_text_and_no_check` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_gate_findings.py::TestPythonForTree::test_uses_tree_venv_python_when_present` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_gate_findings.py::TestPythonForTree::test_falls_back_to_sys_executable_when_no_tree_venv` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_gate_findings.py::TestPythonForTree::test_check_gate_findings_fn_spawns_the_tree_venv_python` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_runner_gate_findings.py::TestPythonForTree::test_check_gates_summary_fn_spawns_the_tree_venv_python` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 13 passed (from 13 evidence id(s))
- gates: 0 error(s), 1214 warning(s), 210 waived
- error-findings: none (measured, zero errors)
