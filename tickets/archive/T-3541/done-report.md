## Done report

MEASURED (run 33353658750): test_directive_continuation_folds_correctly_
not_just_present failed with "cuda's fixture has no continuation" -- the
real fixture source lives in src/frob/gates/_lang_conformance.py's
_CAPABILITY_FIXTURE_SOURCES dict (tests/fixtures/lang/sample.cu, named in
the ticket's own scope, does not exist and is not what this test reads).

Investigated by trying the obvious fix first (copy java/zig's two-line
`// frob:tests \` / `// <target>` continuation shape into cuda's fixture)
and running the actual test: it FAILED differently -- "0 edge(s), 1
malformed, continuation-target-matched=False" -- confirming the
PRE-EXISTING comment on cuda's fixture entry was correct: tree-sitter-
cuda's C-family grammar really does merge the two physical `//`-comment
lines into one token before frob.lang ever sees two lines to fold (the
same quirk c/cpp already carry and are exempted for). The bug was not
the fixture -- it was that the behavioral test's own skip set
(`if language in {"c", "cpp"}: continue`) was never updated when cuda
(T-1602/T-3493) joined the registry with the identical C-family grammar.

Fix: added "cuda" to that skip set (mirrors c/cpp exactly), reverted
the fixture experiment, and added a T-3541 note documenting the
measurement that confirms the quirk is real (not just asserted by
analogy) for cuda specifically.

Evidence:
tests/test_lang_conformance_gate.py::TestBehavioralCapabilityCheck::test_directive_continuation_folds_correctly_not_just_present -- PASS
(the remaining 5 local failures in this file are pre-existing/
environmental: ModuleNotFoundError: strata_core -- this worktree's
native extension was never built, matching the pattern already measured
on every other worktree in this series; frob ticket land auto-rebuilds
natives, as already observed on this series' prior lands)

Filed: none

Gates: frob check --ticket T-3541 --only coverage,drift,docstatus,tickets
clean of any finding against src/frob/gates/_lang_conformance.py or
tests/test_lang_conformance_gate.py.

### Changed
```
 tickets/T-3541/ticket.md | 4 +++-
 1 file changed, 3 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_lang_conformance_gate.py::TestBehavioralCapabilityCheck::test_directive_continuation_folds_correctly_not_just_present` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 26 error(s), 4064 warning(s), 897 waived
- error-findings: ARCH102@src/frob/process/_lock.py, ARCH103@src/frob/tickets/_leases.py, COV001@src/frob/tickets/_land_queue.py, COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DOC001@docs/design/macos-portability.md, DOC007@src/frob/verify/_bisect.py, DOC007@tests/unit/test_process_lock.py, DOCENUM001@docs/modules/gates.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/process/_lock.py, DRIFT002@src/frob/verify/_bisect.py, DRIFT002@tests/unit/test_process_lock.py, DSL001@CHANGELOG.md, LARGE001@.claude/hooks/root-write-guard.py, LARGE001@src/frob/arch/_mayraise.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PII012@tests/test_ticket_leases.py, PRE001@tickets/T-3541, REF001@docs/design/macos-portability.md, REL001@src/frob/__init__.py, SELFAUDIT001@docs/design/registry/capability-via-ratchet.lock.json, TICK004@tickets.md, WAIVE009@src/frob/arch/_normalized.py, WAIVE011@frob-ratchet.lock.json
