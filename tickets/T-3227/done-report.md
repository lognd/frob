## Done report

Re-measured both identities against current main via `frob check --only gates`.

CLAUDE001 .claude/hooks/sync-claude-config.py -- STALE: `claude-config-drift  Claude config in sync with ~/.claude/` passes cleanly. Already resolved by the time this sweep-filed ticket was read.

OPAQUE001 src/frob/app/ticket_runner/_land_cmd.py -- LIVE (not stale, though at a different line than the ticket's own attribution chain -- same file-level identity per this sweep family's own collapse rule). The finding is a functools.partial call whose bound target (_load_parser_factory_from_root) IS statically named; OPAQUE001's resolver just cannot see through any partial's target at all. Bound frob:waive OPAQUE001 with that justification; re-run confirms the finding is now [waived].

Evidence node id tests/test_vet_capability.py::TestX.test_functools_partial_wrapping_dangerous_op_resolves characterizes the functools.partial static-name resolution behavior this waiver's reasoning relies on.

Filed: T-draft-e1bca269 (close-time disclosure check false-positives on split done-report.md -- same tooling bug hit again here, already filed from T-3196)

### Changed
```
 src/frob/app/ticket_runner/_land_cmd.py | 6 ++++++
 tickets/T-3227/ticket.md                | 2 +-
 2 files changed, 7 insertions(+), 1 deletion(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 18 error(s), None warning(s), None waived
- error-findings: CYCLE001@src/frob/__init__.py, invalid-argument-type@src/frob/__main__.py, invalid-argument-type@tests/unit/test_app_runners_batch6.py, invalid-assignment@tests/test_ci_report.py, invalid-assignment@tests/test_tickets_velocity.py, invalid-assignment@tests/test_vet.py, invalid-assignment@tests/unit/verify/test_backpressure.py, unresolved-attribute@tests/unit/test_main_entry.py, unresolved-import@src/frob/arch/_abstraction.py, unresolved-import@src/frob/gates/_vmodel.py, unresolved-import@src/frob/graph/_core.py, unresolved-import@tests/test_arch_near_duplicate_native.py, unresolved-import@tests/unit/strata/test_capacity.py, unresolved-import@tests/unit/test_arch_python_native.py, unresolved-import@tests/unit/test_capability_native.py, unresolved-import@tests/unit/test_dup_core.py, unresolved-import@tests/unit/test_extract_native.py, unresolved-import@tests/unit/test_lang_strata.py
