## Done report

T-2252 was filed as a premise-check finding four independent gaps in
"repoint Makefile at frob quality" (T-2244's leaf): (1) bundled ruff-
check/ruff-format skip flag, (2) `_run_ruff` shelling bare `ruff` instead
of the project-pinned `uv run ruff` (playbook section 12's own drift
hazard), (3) no general ruff-autofix-and-format write mode, (4) no
directory-scoped test SELECTION in `frob quality test`. This ticket had
no formal acceptance criteria of its own (a residue/investigation
filing), so scope was narrowed to the smallest genuinely self-contained,
high-value slice: item (2), the pinned-ruff parity fix -- a real
correctness issue independent of the other three (a bare `ruff` on PATH
can silently disagree with what this repo's own `pyproject.toml` pins,
producing a `frob quality check` verdict that does not match what `uv
run ruff` reports by hand).

Fix: `_run_ruff`/`_ruff_format_result` (src/frob/check/_python.py) now
invoke `uv run ruff` for both the check and format subprocess calls,
never a bare `ruff` argv[0].

Items (1)/(3) (split skip flags + a real ruff write mode) and (4)
(directory-scoped test selection) are each their own distinct,
substantial feature -- filed as separate residue tickets rather than
rushed into this same change: T-2320 (ruff skip-flag split +
write mode) and T-2319 (test-selection scoping). Both name the
exact plumbing gap and the ~120-pre-existing-format-diffs caveat T-2252's
own investigation already measured, so neither needs re-deriving.

Positive control: the existing `test_success_parses_ruff_json_and_
appends_format_result` (unmodified, pre-existing real-behavior test)
still passes unchanged -- the pinned-ruff fix does not alter `_run_ruff`'s
own parsing/result-shape contract, only which `ruff` binary it invokes.

### Changed
```
 tickets/T-2252/ticket.md | 27 ++++++++++++++++++++++++---
 1 file changed, 24 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/unit/test_check.py::TestRunRuffRealPaths::test_invokes_pinned_ruff_via_uv_run_not_bare_ruff` (pytest node id, verified passing when recorded)
- `tests/unit/test_check.py::TestRunRuffRealPaths::test_success_parses_ruff_json_and_appends_format_result` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/release/_cli.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/tickets/_land_git_ops.py, COV001@src/frob/verify/_drain.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, DOC001@docs/commands/release.md, DOC002@src/frob/app/verify_runner.py, DOC002@src/frob/verify/_drain.py, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/gates/_fmt_directives.py, DRIFT002@scripts/fleet_status.py, DRIFT002@src/frob/verify/_drain.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PERF004@src/frob/app/ticket_runner/_new.py, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK004@tickets.md, WIRE003@docs/modules/cli.md
