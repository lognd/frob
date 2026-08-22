## Done report

Root cause verified by direct code reading, per the coordinator's
hypothesis: `_resolve_ticket_root` (`ticket_runner/__init__.py`) checks
the `FROB_ROOT` environment variable BEFORE falling back to `cwd` --
and `spawn_deferred_post_land_sweep`'s `subprocess.Popen` call for the
detached `sweep-async` child passed no `env=` kwarg at all, so it
silently inherited the LANDING process's own bare `os.environ`. When
that ambient environment carried a stale `FROB_ROOT` naming a
different worktree than the already-correctly-resolved `cwd=root`
argument, the child's own root resolution was hijacked by the ambient
value -- `cwd` was right, `FROB_ROOT` overrode it anyway. This is the
single upstream mechanism behind all three symptoms measured in
T-2030's own body: root residue, cross-worktree writes, and the
doubled auto-drop block (all three are the SAME class of write --
landed in the wrong tree because the child resolved its root from the
wrong source).

Fix: `_detached_sweep_env(root)` builds an explicit `env` dict --
`FROB_ROOT` pinned to `root` (wins outright, matching
`_frob_root_env`'s own precedence), `FROB_WORKTREE`/`FROB_AGENT`
stripped (T-0574's worktree-lease env; the detached sweep against the
resolved land root is not "a dispatched worktree agent" and must not
inherit whichever worktree the landing process happened to be leased
to, same T-0880/section-5b precedent this repo already applies to
`tests/system/**`'s own subprocess helper). Passed as `env=` to the
`Popen` call.

Verified the QUEUED/PLANNED state-filter guard (the coordinator's
second question) empirically rather than by reading it: added
`test_a_done_ticket_body_is_byte_for_byte_untouched`, which drives a
ticket to a terminal state and asserts its `ticket.md` bytes are
IDENTICAL before and after `_close_resolved_sweep_tickets` runs. It
passes against both the fixed and unfixed code -- the state filter
itself was never broken; the incident's T-1998 damage came from an
UNRELATED write (some other ticket's own operation) landing in the
wrong tree via the FROB_ROOT hijack this ticket fixes, not from the
state guard failing to protect a candidate it should have skipped.

First test
(`TestDeferredSweepSpawn::test_spawn_pins_frob_root_env_not_bare_os_environ`)
was committed alone against the unfixed code and watched to FAIL (no
`env=` kwarg reached `Popen` at all) before the fix commit was added;
`--check-repro --base-ref <test-only commit>` independently confirmed
`FAILED_AT_PARENT`.

Carries T-2038 as an acknowledged passenger (`--allow-cross-ticket`,
whole-changeset diff verified to contain only these two tickets'
files before acknowledging): T-2038's DRIFT002 fix
(`TestNormalizeIdentityFile`, 3 tests satisfying the `frob:tests`
directives on `_normalize_identity_file` added by T-2036 but never
backed by real tests) is bundled in the same worktree/branch.

The confine-not-just-cleanup point the coordinator raised is addressed
directly: this fix stops the wrong-tree write from ever happening (the
child can no longer resolve the wrong root), which is a different and
prior layer to T-2034's discard-on-commit-failure (which only cleans
up an uncommitted write already correctly addressed to root, and
cannot help a write addressed to the wrong tree in the first place).

### Changed
```
 src/frob/app/ticket_runner/_rapid_sweep.py |  40 +++++++++
 tests/unit/test_rapid_sweep.py             | 135 +++++++++++++++++++++++++++++
 tickets/T-2030/ticket.md                   |  16 +++-
 tickets/T-2038/done-report.md              |  47 ++++++++++
 tickets/T-2038/ticket.md                   |   8 +-
 5 files changed, 243 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/unit/test_rapid_sweep.py::TestDeferredSweepSpawn::test_spawn_pins_frob_root_env_not_bare_os_environ` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestDetachedSweepEnv::test_pins_frob_root_to_the_correct_root` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestDetachedSweepEnv::test_strips_worktree_lease_env` (pytest node id, verified passing when recorded)
- `tests/unit/test_rapid_sweep.py::TestCloseResolvedSweepTickets::test_a_done_ticket_body_is_byte_for_byte_untouched` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH001@src/frob/app/ticket_runner/_query.py, ARCH001@src/frob/app/ticket_runner/_rapid_sweep.py, ARCH103@src/frob/app/ticket_runner/_query.py, F401@/home/logan/projects/frob/.claude/worktrees/sweep-drop-fix/tests/test_gates_fmt_directives.py, F401@/home/logan/projects/frob/.claude/worktrees/sweep-drop-fix/tests/unit/test_tickets_evidence_only_scope.py, PRE001@tickets/T-2030
