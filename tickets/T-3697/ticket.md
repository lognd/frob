---
id: T-3697
title: add frob-directive separator guard (Class::method mistake)
state: in-progress
kind: feature
origin: human
created: '2026-09-02'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .claude/hooks/frob-directive-guard.py
- .claude/settings.json
- tests/test_hook_frob_directive_guard.py
- docs/guides/claude-hooks.md
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: .claude/hooks/frob-suggest.py
  reason: avoid overlap with T-3229/T-3284; going with standalone new hook, not extending
    frob-suggest.py
  actor: logan
  at: '2026-09-02'
- op: add
  glob: docs/guides/claude-hooks.md
  reason: COV001 needs a frob:doc anchor for the new hook's main()
  actor: logan
  at: '2026-09-02'
- op: add
  glob: design/frob.strata
  reason: SELFAUDIT001 requires declaring the new test file's subprocess exec capability
    in the testsuite node
  actor: logan
  at: '2026-09-02'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
The frob:tests Class::method vs Class.method mistake (wrong :: separator) broke FOUR different agents' lands this drive (DRIFT002/DOC007 at land time). Add a WRITE-TIME guard on Write|Edit|Bash that blocks it early: new .claude/hooks/frob-directive-guard.py wired into .claude/settings.json PreToolUse. Detect a frob:tests (or other Class.method-form frob: directive) written with a :: separator between a Class and method (e.g. frob:tests tests/x.py::TestA::test_b where the intra-symbol separator should be . -> TestA.test_b); the FILE::symbol :: boundary IS valid -- only the Class::method double-colon inside the symbol part is wrong. BLOCK (not nudge) with a message showing the corrected form. Study how frob's own frob:tests parser splits path::symbol vs symbol.method (src/frob/, the DOC007/target-form resolver) so the guard matches the parser's grammar, not a naive regex. Add tests: a ::-in-symbol directive blocks; a correct File::Class.method directive passes; a normal edit with no directive passes.