## Done report

The fix landed as an acknowledged passenger commit of T-3675 (round 18)
at logan@logandapp.com's request: T-3675 already held the tests/
conftest.py lease for its own round-18 work, so folding this small,
independent fixture fix into that same worktree avoided a second
serialized lease on the same file. Landed at commit
b50778e45ad9710267f9960d59088f54a8118045 (T-3675's own land, with
--allow-cross-ticket acknowledging T-3666 as a disclosed passenger).

Changed: tests/conftest.py::_write now passes newline="" to
path.write_text, writing every caller's literal \n bytes verbatim
instead of letting win32's default text-mode translation rewrite them
to \r\n. A no-op on POSIX (os.linesep is already \n there).

Evidence: tests/gates_suite/test_fix_engine.py::TestFixEngineTierA::
test_pre_fix_dirty_snapshot_captures_uncommitted_content (one of the
two originally-cited win32 failures; the second test named in this
ticket's body, test_before_snapshot_excludes_litmus_like_the_live_tree,
no longer exists under that name in the current tree -- superseded or
renamed by other work since this ticket was filed, not something this
close touches). Verified passing on this POSIX host (a no-op on POSIX
by design, so this only confirms no regression); the CRLF-specific
behavior is win32-only observable and win32 CI is the actual verifier,
consistent with this ticket's own body.

No behavior change on POSIX; tests/gates_suite/** was not otherwise
touched, per T-3675's own declared out-of-scope list.

### Changed
(no changed files detected)

### Evidence
- `tests/gates_suite/test_fix_engine.py::TestFixEngineTierA::test_pre_fix_dirty_snapshot_captures_uncommitted_content` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 14 error(s), 4253 warning(s), 908 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/check/__init__.py, COV003@tests/test_ci_workflow_matrix.py, COV007@src/frob/strata/_capacity.py, DEPR006@frob-deprecated-baseline.lock.json, DRIFT001@src/frob/process/_derived_lock.py, DRIFT002@docs/modules/process.md, OPAQUE001@src/frob/app/_config_external.py, PERF003@src/frob/refactor/_scan.py, PERF004@src/frob/refactor/_scan_carry.py, REF002@src/frob/process/_lock_msvcrt.py, REL001@src/frob/__init__.py, TEST001@src/frob/strata/_models.py, WAIVE011@frob-ratchet.lock.json
