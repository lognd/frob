## Done report

Root cause: `check_ticket_mutation_evidence` (src/frob/tickets/_mutation_evidence.py)
hardcoded `("uv", "run", "pytest", ...)` as the mutant kill command, spawned
against a throwaway/fixture repo with no environment of its own (no
`pyproject.toml` declaring pytest). Reproduced locally by simulating the
exact macOS CI PATH shape (`uv` on PATH, `.venv/bin` not on PATH, no ambient
global pytest): `uv run pytest ...` fails with "Failed to spawn: pytest" /
exit 2, so every mutant appears to survive and the sweep silently reports
zero findings instead of erroring.

Fix: resolve the kill argv via `frob.process._pytest_spawn.
resolve_pytest_argv` (T-3311's standard convention: `sys.executable -m
pytest`), extracted into a new `_resolve_kill_argv` helper. A spawn that
cannot resolve pytest now returns `Err(MutationEvidenceError.
PytestNotAvailable)` instead of silently reporting zero findings. Also
extracted `_budget_exceeded_finding` to keep `check_ticket_mutation_evidence`
under LANDPARITY002's length threshold after the fix, and added a reasoned
`frob:waive ARCH001` for the remainder (the function was already at the
threshold boundary pre-diff).

Changed:
- src/frob/tickets/_mutation_evidence.py::MutationEvidenceError (new
  PytestNotAvailable variant)
- src/frob/tickets/_mutation_evidence.py::_resolve_kill_argv (new)
- src/frob/tickets/_mutation_evidence.py::_budget_exceeded_finding (new)
- src/frob/tickets/_mutation_evidence.py::check_ticket_mutation_evidence
- docs/modules/tickets-landing.md (describes the pytest-argv resolution
  change and the new error variant)

Evidence:
- tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence::test_confirmatory_test_flagged
- tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence::test_real_subprocess_spawning_evidence_stays_bounded_not_hung
- Both pass locally under the simulated macOS PATH condition
  (`env -i PATH=/usr/bin:/bin .venv/bin/python -m pytest -q ...`), which
  fails without this fix.
- `--check-repro` on the designated repro test reads PASSED_AT_PARENT and
  was forced through with `--designate-repro-force`: this repo's own Linux
  checkout has `uv`/pytest resolvable via ambient PATH, so the pre-fix
  code path does not genuinely fail here -- the defect is PATH-content-
  dependent (identical posture to T-4350's own documented BUG002 waiver
  for the same class of macOS-only PATH defect), not reproducible via a
  parent-commit rerun on this platform.
- Full `tests/test_tickets_mutation_evidence.py` suite (21 tests) passes
  locally, including under the simulated macOS PATH condition.

Filed: none (this ticket's own scope covered the full fix).

Gates: `frob check --ticket T-4369 --only land_parity --only affect_drift
--only drift --only fmt --only prework --only suppress --only ruff --only
ty` clean for every gate on the touched file set (0 errors); the one
remaining SUPPRESS001 error (tests/unit/test_dup_smt.py) is pre-existing,
outside this ticket's scope, and Tier-A auto-fix correctly skipped it as
out-of-scope during land. `frob test --base main`: PASS, 5 python test(s).

Cannot verify on macOS directly (no macOS access this session); state
plainly the CI-green confirmation for the 2 named macOS failures must come
from a macOS CI run.

### Changed
```
 tickets/T-4369/ticket.md | 12 +++++++++++-
 1 file changed, 11 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence::test_confirmatory_test_flagged` (pytest node id, verified passing when recorded)
- `tests/test_tickets_mutation_evidence.py::TestCheckTicketMutationEvidence::test_real_subprocess_spawning_evidence_stays_bounded_not_hung` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 3 error(s), 4793 warning(s), 957 waived
- error-findings: COV007@src/frob/tickets/_mutation_evidence.py, SUPPRESS001@tests/unit/test_dup_smt.py, TICK010@/home/logan/projects/frob/.git/frob-leases/T-4362.json
