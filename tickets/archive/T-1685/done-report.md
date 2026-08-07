## Done report

frob:no-behavior-change reason="all three fixes are behavior-preserving: a type annotation on an existing tuple return, a pure function-boundary split with no logic change, and a doc status-header addition -- none change runtime behavior, so BUG002's designated repro test correctly PASSES at main rather than failing there"

Cleared all three of main's floor errors in one pass:

1. `tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish.
   _land_a_real_ticket` now returns `tuple[str, Path, LandReport]`
   (imported from `frob.tickets._models`) instead of an untyped
   `tuple[str, Path, object]`. `real_report.final_id` at line ~794 now
   narrows correctly under `ty` -- no cast, no suppression. Added a
   one-line docstring to the helper.

2. `src/frob/tickets/_evidence.py::_done_transition_structural_guard`
   split at the same guard boundary its siblings in this module already
   use (e.g. `_done_transition_gate_claim_guard`): the tail half (cmd:
   evidence kind-allowlisting, injected `covers_scope`, unbound
   acceptance criteria) is now its own function,
   `_done_transition_evidence_kind_and_scope_guard`, called from the
   head half. No threshold change, no waiver.

3. `docs/audits/docs-completeness-2026-08-06.md`'s header changed from
   `Status: T-1610` (not a form DOC009's regex recognizes) to
   `Status: 2026-08-06`. Checked first whether T-1610's sweep was
   superseded: T-1610 is `state: done` on main with no successor sweep
   referencing it, so the dated form applies, not SUPERSEDED.

Changed:
- tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish._land_a_real_ticket
- src/frob/tickets/_evidence.py::_done_transition_structural_guard
- src/frob/tickets/_evidence.py::_done_transition_evidence_kind_and_scope_guard
- docs/audits/docs-completeness-2026-08-06.md

Evidence:
- tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish::test_proof_verifies_a_real_land
- tests/test_evidence_integrity.py::TestD02ScopeBinding::test_transition_rejects_when_covers_scope_false
- tests/test_tickets_cmd_evidence.py::TestKindConsistencyAtClose::test_transition_refuses_close_when_kind_flipped_after_recording

Verification:
- `uv run ty check tests/test_ticket_work_and_land_finish.py` -- all checks passed.
- `uv run pytest tests/test_ticket_work_and_land_finish.py -q` -- 30 passed.
- `uv run pytest tests/test_ticket_evidence.py tests/test_tickets_evidence_cli.py tests/test_tickets_cmd_evidence.py tests/test_tickets_gate_claim_evidence.py -q` -- 76 passed.
- `uv run frob check --land-parity` -- clean, 0 unscoped error(s), matches what the land sweep would see.

Filed: T-1726 ("Fix ARCH001/ARCH103/SEC110 drift in
_coverage_refresh.py from T-1677") -- while verifying
`frob check --land-parity`, found 5 new gate errors (2x ARCH001, 2x
ARCH103, 1x SEC110) in src/frob/testing/_coverage_refresh.py, landed
by T-1677 (a separate, already-closed ticket) concurrently with this
ticket's work. Outside T-1685's declared scope (that file is not in
scope=['tests/test_ticket_work_and_land_finish.py',
'src/frob/tickets/_evidence.py',
'docs/audits/docs-completeness-2026-08-06.md']); filed as a new bug
rather than fixed silently, per playbook section 4.

Gates: T-1685's own three targets are clean --
`uv run frob check --only coverage` shows 0 errors for
src/frob/tickets/_evidence.py and
tests/test_ticket_work_and_land_finish.py (COV002 satisfied via new
frob:ticket T-1685 directives); `uv run frob check --only archgate`
shows no ARCH001/ARCH103 finding on
_done_transition_structural_guard/_done_transition_evidence_kind_and_scope_guard;
DOC009 clears for docs/audits/docs-completeness-2026-08-06.md.
`uv run frob check --land-parity` still reports 5 unscoped errors, all
5 attributable to T-1677's _coverage_refresh.py drift (filed above),
none to T-1685's own scope -- main is NOT yet at zero; that residue is
now tracked, not silently absorbed into this ticket. No waivers added.

### Changed
```
 tickets.md | 137 ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++-
 1 file changed, 136 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish::test_proof_verifies_a_real_land` (pytest node id, verified passing when recorded)
- `tests/test_evidence_integrity.py::TestD02ScopeBinding::test_transition_rejects_when_covers_scope_false` (pytest node id, verified passing when recorded)
- `tests/test_tickets_cmd_evidence.py::TestKindConsistencyAtClose::test_transition_refuses_close_when_kind_flipped_after_recording` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 3 error(s), 227 warning(s), 717 waived
- error-findings: ARCH001@src/frob/testing/_coverage_refresh.py, ARCH103@src/frob/testing/_coverage_refresh.py, SEC110@src/frob/testing/_coverage_refresh.py
