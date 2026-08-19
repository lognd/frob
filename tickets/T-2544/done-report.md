## Done report

docs/modules/process.md was held by T-2374's live cross-worktree lease
when T-2537 landed (tool_parse_failure_result, common.py), leaving 4
frob:waive AFFECT001 sites and an undocumented public-api entry. T-2374
has since landed, releasing the lease.

Recovered the drafted prose exactly from commit 84a268696's parent on
branch t-2537 ("chore(parsers): drop docs/modules/process.md edit --
file leased by T-2374") -- diffed it against that commit's own parent to
isolate just the intended insertion (a frob:describes line, the
signature/comment in the public-api code block, and the "Unparsable
output is never silence (T-2537)" subsection), confirmed the surrounding
anchors (tool_crash_result's describes line, its ```python block, the
"## Kill switch" heading) still matched current main byte-for-byte at
the same line numbers, then reapplied that exact text onto the CURRENT
file rather than overwriting it wholesale with the stale historical
snapshot (main had diverged elsewhere since T-2537's commit).

Removed the 4 frob:waive AFFECT001 lines this doc update makes
unnecessary (src/frob/process/parsers/common.py, eslint.py, junit.py,
ruff.py) -- each site's frob:doc edge now resolves against the real
docs/modules/process.md#public-api anchor.

DOC006 (recognized-pointer-shape gate): 0 findings against
docs/modules/process.md, verified directly. tests/unit/
test_parser_failure_diagnostics.py (16 tests, the existing coverage for
tool_parse_failure_result and its 4 call sites) still passes unchanged.

### Evidence
cmd:uv run pytest tests/unit/test_parser_failure_diagnostics.py -q
exit=0 (docs-kind ticket, non-pytest evidence channel)

### Changed
```
 docs/modules/process.md            | 21 +++++++++++++++++++++
 src/frob/process/parsers/common.py |  3 ---
 src/frob/process/parsers/eslint.py |  3 ---
 src/frob/process/parsers/junit.py  |  3 ---
 src/frob/process/parsers/ruff.py   |  3 ---
 tickets/T-2544/ticket.md           |  4 +++-
 6 files changed, 24 insertions(+), 13 deletions(-)
```

### Evidence
- `cmd:uv run pytest tests/unit/test_parser_failure_diagnostics.py -q exit=0 sha256=e6894dd97db4` (cmd evidence, exit=0)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2561/ticket.md, DOC006@tickets/T-2565/ticket.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2544/src/frob/app/ticket_runner/_verify.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2544/src/frob/scaffold/project.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
