## Done report

Wired frob ticket scope --demote-to-evidence-only GLOB... to T-1944's demote_to_evidence_only: new CLI flag in _add_ticket_scope_parser (_metadata.py), new AppConfig field, runner-side dispatch in _mutate.py (_apply_demote_to_evidence_only, split out from _scope for ARCH001), and registered in _config_external.py's _LIST_FIELDS (WIRE001's own requirement -- confirmed the field would otherwise be silently dropped by AppConfig.from_external before AppConfig(**d), T-1422's shape). Combinable with --add/--remove in the same call: demote runs first, then add/remove if also given. Proof of CLI wiring (not just the already-tested library function): test_cli_demote_to_evidence_only_releases_lease drives the real _scope entrypoint end to end and asserts the glob actually moved from scope to evidence_scope; test_cli_demote_to_evidence_only_requires_declared_glob proves an undeclared glob still refuses through the CLI path, matching demote_to_evidence_only's own ScopeRemoveNotDeclared guard.

### Changed
```
 tickets/T-1975/ticket.md           | 40 +++++++++++++++++++++++++++++++++++++-
 tickets/T-2009/ticket.md | 21 ++++++++++++++++++++
 2 files changed, 60 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_tickets_scope_mutation.py::TestScopeCli::test_cli_demote_to_evidence_only_releases_lease` (pytest node id, verified passing when recorded)
- `tests/test_tickets_scope_mutation.py::TestScopeCli::test_cli_demote_to_evidence_only_requires_declared_glob` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: DSL001@CHANGELOG.md, F401@/home/logan/projects/frob/.claude/worktrees/ticket-workflow/tests/unit/test_tickets_evidence_only_scope.py, invalid-argument-type@src/frob/app/ticket_runner/_mutate.py
