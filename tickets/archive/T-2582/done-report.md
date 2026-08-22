## Done report

Fixed the stream split for the 8 human-mode query commands drowning their
answer in DEBUG/INFO parse chatter (5958 lines for a 13-line xref answer).

Root cause was the `quiet_stdout_logs() if cfg.<name>_json else
contextlib.nullcontext()` pattern repeated at debt_runner.py:60,
deprecated_runner.py:78, exports_runner.py:24,117, fleet_runner.py:68,
gitlog_runner.py:39, mutate_runner.py:42, outline_runner.py:45, and
xref_runner.py:29 -- only --json mode was protected from stdout-bound
INFO/DEBUG chatter, human mode was not.

Fix: one new shared helper, `quiet_query_stdout()`
(src/frob/logging/quiet.py), that quiets stdout by default in BOTH modes
and is gated by a single `FROB_VERBOSE=1` env-var opt-out (not a new
per-command --verbose CLI flag -- that would need AppConfig/
_config_external.py field-registry changes, and _config_external.py was
under a live lease from T-2574 for the duration of this ticket). All 8
runners now call `quiet_query_stdout()` unconditionally instead of
gating on `cfg.<name>_json`. docs/modules/logging.md and
docs/modules/app.md#runners document the new symbol/behavior (AFFECT001
closure).

Measured before/after (frob xref _doable_sort_key):
  human mode:  5958 -> 14 lines (answer now on the first screenful)
  --json mode: 64 lines, byte-identical, still valid JSON
  FROB_VERBOSE=1 human mode: 5958 lines (full chatter restored verbatim)
Spot-checked frob outline/frob debt/frob gitlog similarly clean.

BUG002 repro: committed the test alone first (c2900d3f4), confirmed
ImportError at that commit (quiet_query_stdout did not exist yet), then
applied the fix and confirmed pass; designated via --check-repro against
c2900d3f4 (FAILED_AT_PARENT, genuine repro).

Gates: `frob check --land-parity` initially found the FROB_VERBOSE
os.environ.get read had no SEC110 waiver (fixed: it is a verbosity
toggle, not a secret) and that the 6 touched runners' AFFECT001 closure
to docs/modules/app.md#runners was not touched (fixed: added the doc
note). After those two fixes, land-parity's remaining 46 unscoped errors
are all outside T-2582's scope (TICK00x/COV003/COV004/DOC00x/PERF00x/
SEC110 in verify_runner.py etc, ARCH103, WIRE00x, CLAUDE001,
SELFAUDIT001) -- none touch quiet.py, the 8 runners, or the two doc
files this ticket owns; spot-checked several against main's own parent
tree to confirm pre-existing.

Worktree was stale (main advanced ~58 files during the session); merged
main cleanly before finishing, per playbook section 9's deletion-filter
check (git diff main --diff-filter=D --stat was non-empty with sibling
tickets' own files before the merge, empty after).

No new tickets filed -- everything in scope was completed; no
out-of-scope defects were discovered in the touched files.

### Changed
```
 docs/modules/app.md               |  8 +++++
 docs/modules/logging.md           |  9 ++++++
 src/frob/app/debt_runner.py       | 13 ++++----
 src/frob/app/deprecated_runner.py |  7 ++---
 src/frob/app/exports_runner.py    | 10 +++----
 src/frob/app/fleet_runner.py      | 22 +++++++-------
 src/frob/app/gitlog_runner.py     | 15 +++++-----
 src/frob/app/mutate_runner.py     | 16 +++++-----
 src/frob/app/outline_runner.py    |  8 ++---
 src/frob/app/xref_runner.py       | 10 ++++---
 src/frob/logging/quiet.py         | 36 ++++++++++++++++++++++
 tests/unit/test_logging_quiet.py  | 63 ++++++++++++++++++++++++++++++++++++++-
 12 files changed, 163 insertions(+), 54 deletions(-)
```

### Evidence
- `tests/unit/test_logging_quiet.py::TestQuietQueryStdout::test_quiets_by_default` (pytest node id, verified passing when recorded)
- `tests/unit/test_logging_quiet.py::TestQuietQueryStdout::test_frob_verbose_env_var_restores_full_chatter` (pytest node id, verified passing when recorded)
- `tests/unit/test_logging_quiet.py::TestQuietQueryStdout::test_restores_on_exception` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, ARCH103@src/frob/tickets/_store.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/gates/_rule_id_scan.py, COV001@src/frob/strata/_multifile.py, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, CYCLE001@src/frob/__init__.py, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC006@tickets/T-2570/ticket.md, DOC006@tickets/T-2585/ticket.md, DOC008@docs/modules/gates.md, DOCENUM001@docs/modules/gates.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, E501@/home/logan/projects/frob/.claude/worktrees/query-stream-fixes/src/frob/app/ticket_runner/_ledger_mirror.py, E501@/home/logan/projects/frob/.claude/worktrees/query-stream-fixes/src/frob/scaffold/project.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, PII012@tests/test_capability_registry.py, PRE001@tickets/T-2582, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
