## Done report

## Done report

Changed:
  src/frob/gates/__init__.py::ticket_lease_pin
  src/frob/app/check_runner.py::_refuse_ticket_lease_mismatch
  src/frob/app/check_runner.py::run (wired the new refusal before any stage/run_gates call)

Wiring design: `ticket_lease_pin(root, ticket_id)` (new, gates/__init__.py, exported
via __all__) wraps T-0766's resolve_lease. It passes through Ok(None) both when the
resolved worktree pins cleanly AND when the cross-worktree lease mechanism has never
been engaged at all in this repo (no shared git common dir, or a leases directory
that has never been created because no ticket has ever been `frob ticket start`ed
anywhere) -- this is what keeps non-agent/plain-repo invocations working unchanged
per the acceptance criterion. Once the mechanism IS engaged (the leases directory
exists) it returns Err(NoLeaseForTicket) or Err(LeaseWorktreeMismatch) exactly as
resolve_lease itself does. `_refuse_ticket_lease_mismatch(root, cfg)` (new,
check_runner.py) is the CLI-boundary caller: it resolves the active ticket the same
way `run_gates` does (`frob.gates.active_ticket(root, cfg.check_ticket)`), and when
one resolves, calls `ticket_lease_pin`; any Err logs a loud message naming
`frob ticket start <ticket_id>` and the underlying LeaseError text. `run()` calls
this immediately after the `--only list`/agent-refusal checks and before
`_handle_stamp_modes`/any stage dispatch, so both a full run and `--stamp-baseline`
are covered by one choke point, matching every other early-refusal check in this
module. No changes to src/frob/gates/_models.py (GateError) -- reusing/adding a
GateError variant would have required editing a file outside T-0787's declared
scope and risked colliding with the unrelated existing WorktreeLeaseViolation
(FROB_WORKTREE env-var) mechanism; the CLI-boundary refusal achieves the same
loud-refusal contract without touching it.

Evidence (tests/test_tickets_leases.py, all pytest -p no:cacheprovider -q, 21/21 pass
including pre-existing TestResolveLease/TestReadAllLeasesSiblingProcessVisibility):
  TestTicketLeasePin::test_no_lease_mechanism_engaged_passes_through
  TestTicketLeasePin::test_pinned_lease_for_this_worktree_passes
  TestTicketLeasePin::test_lease_absent_for_this_worktree_refuses
  TestTicketLeasePin::test_lease_recorded_elsewhere_refuses
  TestCheckTicketLeaseCli::test_pins_to_own_worktree_lease
  TestCheckTicketLeaseCli::test_refuses_when_lease_recorded_for_another_worktree
  TestCheckTicketLeaseCli::test_no_ticket_resolved_skips_the_check_entirely
Bound to acceptance[0] via `frob ticket evidence T-0787 ... --accepts 0`.

`uv run --frozen frob test --base main`: python exit=1 -- 3 pre-existing failures
unrelated to T-0787 (TestCheckCleanProject::test_clean_code_exits_zero,
TestCheckStampBaselineAndDelta::test_delta_reports_only_new_violation,
TestCheckPolyglot::test_unpinned_polyglot_runs_python_stage). Verified unrelated by
temporarily reverting the two lines in check_runner.py::run that call
_refuse_ticket_lease_mismatch and re-running the same three tests: all three fail
identically without T-0787's change in place (pre-existing "not a git repository"/
stray gitio debug-line-in-stdout breakage in TestCheckCleanProject's tmp_path
fixture, unrelated to leases). Re-verified my own new tests pass both with and
without that revert cycle.

Gates: `uv run --frozen frob check --ticket T-0787 --only lint|static|gates-fast|
gates-native|gates-security`, chunked, all clean for T-0787's own scope after two
fixes made along the way:
  - ruff-format: reformatted tests/test_tickets_leases.py (line-length wrap).
  - DRIFT002 (gate:DRIFT, 6 violations): my initial `frob:tests` directives used
    `path::Class::method` (double `::`) instead of this repo's actual qualname
    convention `path::Class.method` (dot before the method) -- fixed in both
    gates/__init__.py and check_runner.py; re-verified 0 DRIFT violations after a
    graph cache rebuild (`rm -f .frob/cache.db`).
  - PRE001 (stale pre-work sweep): re-ran `frob ticket sweep T-0787` after adding
    the new symbols; clean afterward.
  - SCOPE001/uv.lock and a stray `uv.lock` version-line diff (0.101.0 -> 0.102.0):
    both were side effects of `make core`/`uv sync` in this worktree, not my own
    edits -- `git checkout -- uv.lock` before every check/finish, per playbook 4b
    (land-owned file). Re-appeared once more after a later `pytest` run and was
    reverted again before finishing; confirmed 0 remaining diff on uv.lock at
    finish time.
  - REL001 (public API changed, minor bump needed) still fires: this worktree's
    shell does not actually have FROB_AGENT set (despite being a dispatched
    worktree agent), so REL001's bump/changelog suppression half never engaged.
    Per the dispatch instructions and playbook 4b, land computes the bump
    automatically -- disclosing rather than hand-bumping pyproject.toml/
    CHANGELOG.md/uv.lock myself.
  - `git diff main --diff-filter=D --stat`: empty (playbook section 9 check).

Filed: none -- no out-of-scope findings.

### Changed
(no changed files detected)

### Evidence
- `tests/test_tickets_leases.py::TestTicketLeasePin::test_no_lease_mechanism_engaged_passes_through` (pytest node id, verified passing when recorded)
- `tests/test_tickets_leases.py::TestTicketLeasePin::test_pinned_lease_for_this_worktree_passes` (pytest node id, verified passing when recorded)
- `tests/test_tickets_leases.py::TestTicketLeasePin::test_lease_absent_for_this_worktree_refuses` (pytest node id, verified passing when recorded)
- `tests/test_tickets_leases.py::TestTicketLeasePin::test_lease_recorded_elsewhere_refuses` (pytest node id, verified passing when recorded)
- `tests/test_tickets_leases.py::TestCheckTicketLeaseCli::test_pins_to_own_worktree_lease` (pytest node id, verified passing when recorded)
- `tests/test_tickets_leases.py::TestCheckTicketLeaseCli::test_refuses_when_lease_recorded_for_another_worktree` (pytest node id, verified passing when recorded)
- `tests/test_tickets_leases.py::TestCheckTicketLeaseCli::test_no_ticket_resolved_skips_the_check_entirely` (pytest node id, verified passing when recorded)
