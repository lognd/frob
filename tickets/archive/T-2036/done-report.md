## Done report

Root cause (measured against T-2022's own filed body vs a re-measurement
on main): `_rapid_sweep.py`'s `(rule, file)` identity comparisons
(`vanished = baseline - fresh`, `identities <= vanished`) are plain
tuple equality, and a diagnostic's `file` field is not guaranteed to
render the same way (absolute vs repo-relative) across two separate
`frob check` spawns. Format drift between two sweep runs makes a
still-broken file's identity silently "vanish" from the diff, and the
ticket that named it is auto-dropped on a false premise -- confirmed
directly against T-2022 (filed with two absolute-path F401 identities;
both still reproduce on main today via a direct `ruff check`).

Added `_normalize_identity_file` / `_normalize_identities` and routed
every point `_rapid_sweep.py` constructs or reads a `(rule, file)`
identity set through them: the fresh unscoped measurement
(`run_deferred_post_land_sweep`), the persisted rolling baseline (both
`_read_baseline` and the write path, since `fresh` is normalized
before `_write_baseline` runs), and identities parsed back out of a
previously-filed ticket's body in BOTH call sites of
`_maybe_drop_resolved_ticket`'s caller (the T-1983 sweep path and the
T-2006 `doable` path) -- so a ticket filed before this fix, still
carrying an absolute path, now compares correctly against a
freshly-normalized set.

First test
(`TestAbsoluteVsRelativePathIdentityMismatch::test_format_drift_between_sweeps_does_not_falsely_resolve_a_live_ticket`)
was committed alone against the unfixed code and watched to FAIL (the
still-broken ticket ended up state DROPPED, not QUEUED) before the fix
commit was added; `--check-repro --base-ref <test-only commit>`
independently confirmed `FAILED_AT_PARENT`.

DISCLOSED CUT: T-2022 itself was NOT reopened in this land. Its scope
(`tests/test_gates_fmt_directives.py`,
`tests/unit/test_tickets_evidence_only_scope.py`, `tickets/T-0907`)
does not overlap this ticket's declared scope
(`src/frob/app/ticket_runner/_rapid_sweep.py`), and this worktree's
CLI exposed no `reopen` verb for a `dropped` ticket -- only
`plan`/`start`/`close`/`drop`.

Filed: T-2037

NOT fixed here (explicitly out of scope, filed separately): T-2030,
the sweep writing into a concurrent agent's own worktree -- a
root-path-resolution defect the coordinator suspects shares an
upstream cause with this ticket's own false-drop, but which was not
independently investigated in the time available this session.

### Changed
(no changed files detected)

### Evidence
- `tests/unit/test_rapid_sweep.py::TestAbsoluteVsRelativePathIdentityMismatch::test_format_drift_between_sweeps_does_not_falsely_resolve_a_live_ticket` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/app/ticket_runner/_query.py, ARCH001@src/frob/app/ticket_runner/_rapid_sweep.py, ARCH103@src/frob/app/ticket_runner/_query.py, DRIFT002@src/frob/app/ticket_runner/_rapid_sweep.py, F401@/home/logan/projects/frob/tests/test_gates_fmt_directives.py, F401@/home/logan/projects/frob/tests/unit/test_tickets_evidence_only_scope.py, PRE001@tickets/T-2036
