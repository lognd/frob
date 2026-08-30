## Done report

No code change needed: the DESCRIBED WORK T-draft-36006d55 was supposed
to cover already exists and passes on main.

T-3031's Done report claimed a third ticket (T-draft-36006d55, "gets a
real id at land/renumber") was filed for
TestGitlessTargetGateSeverity::test_render_lint_gate_warns_not_errors_...
-- that draft id never resolves to any block in tickets.md or
tickets-archive.md, a phantom filing trail (most likely: the draft was
promoted to a real id at renumber time and its ORIGINATING claim text
was never updated to match, or the work was folded directly into
T-3031's own landed diff without ever needing its own separate ticket).

VERIFIED the actual test exists and is wired correctly:
tests/system/test_cli_check.py::TestGitlessTargetGateSeverity contains
both test_gitless_target_gates_warn_not_error and
test_render_lint_gate_warns_not_errors_on_gitless_root, both anchored to
docs/modules/gates.md#git-less-target-contract-t-0705 (T-0705's own git-
less-target contract), and both pass.

Recorded a failure attempt first (this session) since no NEW work was
produced by this ticket; closing now with the pre-existing test bound as
evidence and this Done report, so the phantom-citation trail is
terminated on main rather than left dangling for the next TICK006 sweep
to re-surface.

`uv run pytest -p no:xdist tests/system/test_cli_check.py::TestGitlessTargetGateSeverity -v`: 2 passed.

### Changed
```
 tickets/T-3242/ticket.md | 15 +++++++++++----
 1 file changed, 11 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/system/test_cli_check.py::TestGitlessTargetGateSeverity::test_gitless_target_gates_warn_not_error` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_check.py::TestGitlessTargetGateSeverity::test_render_lint_gate_warns_not_errors_on_gitless_root` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 12 error(s), 3965 warning(s), 856 waived
- error-findings: COV003@tickets/T-3410, DEPR006@frob-deprecated-baseline.lock.json, DOC006@docs/design/windows-portability.md, DOC006@tickets/T-3411/ticket.md, DOC006@tickets/T-3424/ticket.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, REL001@src/frob/__init__.py, SELFAUDIT001@design, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json, unresolved-attribute@tests/system/test_coverage_sigterm.py
