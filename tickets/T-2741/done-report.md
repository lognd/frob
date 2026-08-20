## Done report

Both PII012 sites T-2712 could not touch:

1. src/frob/serve/_socketd.py:530 (`allow_reuse_address = True`) --
   DSL-placement mismatch: `comment.following` binds a comment above a
   plain class-attribute assignment to the NEXT def/class construct
   (`_DaemonServer.__init__`), never to the enclosing class or the
   assignment itself, while the violation's own `enclosing_qualname`
   symref is just `_DaemonServer` (no enclosing function). Moved the
   waiver comment to directly above `class _DaemonServer(...):` --
   `comment.following` there resolves via_following straight to
   `_DaemonServer`, matching the violation's exact symref (T-2438's
   exact-match rule), the same placement PLACE001's own docstring
   documents as correct for a class-level directive. No detector code
   touched.

2. tests/test_capability_registry.py:902
   (`test_secretsmanager_put_secret_value_reports_net_mutate`) -- no
   existing waiver; added `frob:waive PII012` above the def, reason
   naming the specific false-positive mechanism (AWS Secrets Manager
   API name matched via the "secret" keyword substring, not a real
   credential).

Verified: `frob check --only pii_structural --no-cache` shows zero
PII (error-severity) findings at either site (both now waived, visible
only as note-severity suggestions like every other T-2712-resolved
site). Both touched tests pass directly. Did not touch detector code
in either fix -- pure waiver-comment placement/addition, so no
positive-control fixture was needed (T-2712 already established the
detector still fires generally; these two changes cannot narrow it,
they only add exact-match waivers at two named sites).

Changed:
  src/frob/serve/_socketd.py
  tests/test_capability_registry.py

Evidence:
  tests/test_capability_registry.py::TestBoto3NextTierServiceBindingResolution::test_secretsmanager_put_secret_value_reports_net_mutate

Filed: none.

Gates: `frob check --only pii_structural --no-cache` clean of both
named identities (0 errors); severity dropped to note at both sites,
matching T-2712's own precedent for the other 19 resolved findings.

### Changed
```
 tickets/T-2741/ticket.md | 4 +++-
 1 file changed, 3 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_capability_registry.py::TestBoto3NextTierServiceBindingResolution::test_secretsmanager_put_secret_value_reports_net_mutate` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 19 error(s), 880 warning(s), 707 waived
- error-findings: ARCH103@src/frob/app/ticket_runner/_close_cmd.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1688, COV003@tickets/T-2365, CYCLE001@src/frob/__init__.py, DOC006@tickets/T-2742/ticket.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, DRIFT002@src/frob/tickets/_land.py, PRE001@tickets/T-2741, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md
