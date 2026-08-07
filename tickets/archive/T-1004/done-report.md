## Done report

Two-part fix for coordination-churn audit item 5 (harness auto-background stalls).

(a) Rewrote docs/guides/agent-playbook.md section 3b: renamed it from
"never background a verification" to "foreground + explicit timeout
wrapper is the ONLY sanctioned pattern", removed all backgrounding-as-
normal framing, added timeout-wrapped command examples throughout
(section 3b and section 6's --stamp-baseline/--delta recipes), and
inlined two concrete recipes agents can copy: Recipe 1 is the new
`--budget` mode, Recipe 2 is the existing T-0627 manual --only loop
(deduplicated -- the old file had this loop listed twice, once before
and once after the --stamp-baseline chunking paragraph; kept one copy).
docs/commands/check.md documents the new --budget flag under Usage.

(b) Implemented `frob check --budget SECONDS` in
src/frob/app/check_runner.py: self-selects and greedily packs
`frob.check.available_stages()` groups to fit SECONDS using a persisted
rolling EMA of measured per-group wall time
(.frob/check-budget-timing.json, seeded from a 90s default per group
until measured), runs the selected subset in one foreground process,
and persists whatever did not fit as resume state
(.frob/check-budget-state.json) that the next --budget invocation
continues from. Deferred groups are reported via a BUDGET001 warning
ToolResult naming every one of them -- never a silent drop. CLI wiring
(--budget SECONDS in src/frob/__main__.py, AppConfig.check_budget in
src/frob/app/config.py) required expanding the ticket's declared scope
via `frob ticket scope --add` (recorded in the ticket's scope_changes
audit trail) since neither file was in the original scope but both are
structurally required to expose a new CLI flag.

Dogfooded end-to-end against this repo's own tree with
`timeout 100 uv run frob check --ticket T-1004 --budget 90`, run
repeatedly: first call ran gates-fast (48s measured) and deferred the
rest with a loud BUDGET001 line; each subsequent call consumed one more
group from resume state (gates-native, gates-security, lint, static)
until nothing remained and check-budget-state.json was deleted;
check-budget-timing.json ended up with real measured seconds per group
(gates-fast=48.5s, gates-native=33.5s, gates-security=22.0s, lint=1.3s,
static=48.5s). No scope-relevant gate errors surfaced in any of those
scoped runs (`gate:ARCH`'s one-error blip during an early --only-scoped
gates-native run was a WAIVE004 flaky-under---only finding the gate's
own message explicitly calls out as "trust this only from a full,
unscoped run" -- not present when the same gate ran again, and not
touched by this ticket's scope).

### Changed
```
 tickets.md | 204 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++--
 1 file changed, 198 insertions(+), 6 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 13 passed (from 13 evidence id(s))
- gates: 3 error(s), 4442 warning(s), 325 waived
- error-findings: COV003@tickets/T-1000, COV003@tickets/T-1001, COV003@tickets/T-1003
