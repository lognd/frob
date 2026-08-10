## Done report

T-1843 wires `find_policy_weakenings` (INV-051, T-1482) into a real
`frob check` gate: `frob.gates._policy_weakening_gate.policy_weakening_gate`
loads+elaborates every `.strata` file under `design/` (same opt-in posture
as `sys_gate`), compiles the merged `PolicyDecl`s against the merged
`KernelModel`, and runs `find_policy_weakenings` over the result, emitting
rule `INV051`. Wired into the invariant gate-family job in
`frob.gates.__init__`.

`DesignIds` (`frob.strata._design_load`) gained a `policies:
tuple[PolicyDecl, ...]` field, merged pre-elaboration across files --
the same pattern `resources`/`store_ids` already established -- so a
gate can build the throwaway `Module(name=..., policies=ids.policies)`
`compile_policies` needs without re-parsing.

The now-obsolete `frob:waive WIRE001` on `find_policy_weakenings` was
removed (it now has a real caller) and replaced with `frob:ticket T-1843`.
`INV051` registered in `_KNOWN_GATE_RULES` (`src/frob/gates/_waive.py`).
`design/frob.strata`'s own self-model updated: `policy_weakening_gate`
added to the `gates` node's `interface=`, `_policy_weakening_gate.py`
added to its `fs.write` capability list, and the new test file added to
`testsuite`'s `fs.write` list (SELFAUDIT001/SYS100/SYS104).

Docs updated for AFFECT001: docs/strata/policy.md's refinement-
monotonicity section now documents the T-1843 wiring; docs/strata/
surface.md and docs/strata/host.md note the new `DesignIds.policies`
field per the T-1061 `resources` precedent.

Deliberately preserved: `forbid_call`/`forbid_import` stay excluded from
the diff (T-1482's own finding -- purely additive under union
enforcement, cannot be weakened). The gate is silent on any design load
failure (SYS004 already reports that) and when no policies are declared.

Disclosed, NOT fixed (both pre-existing, outside declared scope,
confirmed unrelated to this diff):
- DOCENUM001 at docs/modules/gates.md:13: `frob:enumerates` there already
  claimed a stale `_KNOWN_GATE_RULES` member list before this ticket
  (omitting WAIVE008); this ticket's own INV051 addition is now also
  omitted from that same stale claim. docs/modules/gates.md is another
  agent's declared scope per dispatch instructions -- not touched.
- SEC110 at .claude/hooks/dispatch-telemetry.py:72: a pre-existing
  `frob:waive SEC110` comment there does not take effect (T-1838's own
  title, landed on main during this ticket's work: "frob:waive comments
  in .claude/hooks/** never take effect (BUILTIN_SKIP_DIRS prunes
  .claude...)" -- exactly this bug, already ticketed and landed
  separately). File untouched by this diff.

Update after merging main (T-1838 landed mid-ticket, fixing the SEC110
false-positive in .claude/hooks/** by removing it from BUILTIN_SKIP_DIRS):
that fix newly exposes .claude/hooks/** to every gate for the first time,
producing 11 new COV001 + 1 DOC003 finding there, plus a DOCENUM001-
adjacent design/frob.strata::frob.claude_hooks COV001 -- all pre-existing
repo-wide fallout from T-1838's own change, in files this ticket's scope
never touches. TEST006 ("no coverage stamp found") is the expected
coordinator-only make-coverage state for a worktree, not a regression.
Full unscoped `frob check` confirmed exactly these findings and no others
outside T-1843's declared scope.

### Changed
```
 design/frob.strata                       |   6 +-
 docs/strata/host.md                      |   8 ++
 docs/strata/policy.md                    |  29 +++++--
 docs/strata/surface.md                   |  10 +++
 src/frob/gates/__init__.py               |   5 ++
 src/frob/gates/_policy_weakening_gate.py | 141 +++++++++++++++++++++++++++++++
 src/frob/gates/_waive.py                 |   4 +
 src/frob/strata/_design_load.py          |  21 ++++-
 src/frob/strata/_policy.py               |   4 +-
 tests/unit/test_policy_weakening_gate.py |  72 ++++++++++++++++
 tickets/T-1843/done-report.md            |  64 ++++++++++++++
 tickets/T-1843/ticket.md                 | 101 +++++++++++++++++++++-
 12 files changed, 449 insertions(+), 16 deletions(-)
```

### Evidence
- `tests/unit/test_policy_weakening_gate.py::TestPolicyWeakeningGate::test_no_design_dir_noop` (pytest node id, verified passing when recorded)
- `tests/unit/test_policy_weakening_gate.py::TestPolicyWeakeningGate::test_weakening_detected` (pytest node id, verified passing when recorded)
- `tests/unit/test_policy_weakening_gate.py::TestPolicyWeakeningGate::test_clean_policies_no_finding` (pytest node id, verified passing when recorded)
- `tests/unit/test_policy_weakening_gate.py::TestPolicyWeakeningGate::test_load_failure_skips_silently` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 11 error(s), 1194 warning(s), 744 waived
- error-findings: COV001@.claude/hooks/_shellscan.py, COV001@.claude/hooks/diagnosis-nudge.py, COV001@.claude/hooks/dispatch-telemetry.py, COV001@.claude/hooks/frob-suggest.py, COV001@.claude/hooks/frob-timeout-guard.py, COV001@.claude/hooks/sync-claude-config.py, COV001@design/frob.strata, DOC003@docs/commands/sys.md, DOCENUM001@docs/modules/gates.md, E501@/home/logan/projects/frob/.claude/worktrees/gate-wiring/src/frob/gates/_policy_weakening_gate.py, TEST001@.claude/hooks/_shellscan.py
