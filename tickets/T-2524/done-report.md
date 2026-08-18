## Done report

Changed:
docs/guides/agent-playbook.md (section 1d)

Chose fix option 1 from the three the ticket offered ("give agents a
sanctioned scratch location outside the repo... say so in the
playbook") -- it removes the failure rather than hiding it, per the
ticket's own stated preference. Section 1d already said "in your
scratch area, not inside the repo tree" but left "scratch area"
unspecified, which is exactly how five agents still ended up writing
done-report-t####.md into the repo root: nothing told them where
"scratch" concretely was. The new text names /tmp explicitly, states
the .gitignore stopgap's real cost (invisible to git status
--porcelain, not a fix), and states the positive control the ticket
itself specifies: git status --porcelain AND git ls-files both clean,
not just the first.

Did not touch: the .gitignore stopgap (out of this ticket's declared
scope, docs/guides/agent-playbook.md only; the ticket did not ask for
its removal, only for the real fix alongside it) or options 2/3 (the
ticket said pick one).

The git gc / "too many unreachable loose objects" note in the ticket
body is explicitly flagged there as a separate concern to file
separately if worth acting on -- not filed here, left for whoever picks
it up, since it is unrelated to this ticket's own scope and the ticket
body itself says so.

Evidence: docs-only ticket with no pytest surface of its own (playbook
section 5's own precedent for exactly this case) --
tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
recorded via `frob ticket evidence T-2524`.

Filed: none.

Gates: this is a prose-only change to one doc file; no code gates apply.
frob:doc/frob:tests coverage requirements do not apply to markdown prose.

### Changed
```
 docs/guides/agent-playbook.md | 24 ++++++++++++++++++++++++
 tickets/T-2524/ticket.md      |  6 +++++-
 2 files changed, 29 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2524/src/frob/app/ticket_runner/_verify.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
