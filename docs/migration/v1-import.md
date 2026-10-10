# v1 ticket import

Status: historical
Owner: frob
Decisions: none
Audience: contributor

Written by `cargo dev import-v1-tickets` (T-0025). Every v1 ticket became a v2 ULID ticket whose `aliases` hold the v1 id, so `frob ticket show T-0003` resolves. The v1 ledger itself stays in git history before the import commit.

## Identity and time

v1 keeps only a creation date. A ticket ULID carries that date at 00:00:00 UTC plus the v1 ticket number as milliseconds, so creation order is preserved and ids never share a prefix. Event `i` of a ticket sits `i` seconds after the date (ULID time and `at` agree). These instants are synthetic; real times are in git history.

## Field mapping

| v1 | v2 |
|---|---|
| `kind` feature, ux | type `task` (ux also sets flavour `ux`) |
| `kind` bug, security, docs, invariant, incident | the same type |
| `tier` epic, story | type `epic`, `story` (wins over `kind`) |
| `state` queued, planned, in-progress | category `todo` (leases do not carry over) |
| `state` done, archived | category `done`, outcome `done` |
| `state` dropped | category `done`, outcome `wont-fix`, drop reason kept as a comment event |
| `blocked_by`, `parent` | `blocked-by` links, `parent` (mapped through the id map) |
| `milestone`, `component` | labels `milestone:<v>`, `component:<v>` |
| `origin` | actor of the `create` event and reporter |
| `acceptance` | acceptance criteria with `bound = false` |
| `evidence` (`cmd:` lines) | `evidence` events, provider `command`, status measured when exit is 0 |
| `done-report.md` | `decision` comment event titled `v1 done-report` |
| body | the markdown body |

## Result

35 tickets and 127 events. By type: bug 5, docs 1, epic 2, task 27. By category: done/done 29, done/wont-fix 2, todo 4.

## Dropped v1 fields

| v1 field | Tickets with a value | Why it is not carried |
|---|---|---|
| `worktree` | 30 | per-checkout lease state; v2 leases are local runtime state and worktrees derive from the handle |
| `branch` | 30 | per-checkout lease state; v2 derives the branch name from the handle |
| `sprint` | 0 | v2 has no sprint field (cycles arrive in milestone 2) |
| `due` | 0 | v2 has no due-date field |
| `rank` | 0 | v2 orders by priority and points; no manual rank |
| `runs_last` | 0 | v1 scheduling hint; v2 leases replace the run-last queue |
| `runs_last_parallel_safe` | 0 | v1 scheduling hint with no v2 equivalent |
| `runs_last_parallel_safe_reason` | 0 | reason for a dropped v1 scheduling hint |
| `unsized_ack` | 0 | v1 sizing-gate waiver; v2 has no sizing gate |
| `unsized_ack_reason` | 0 | reason for a dropped v1 sizing-gate waiver |
| `tokens_in` | 0 | v1 cost telemetry; v2 cost events arrive in milestone 2 |
| `tokens_out` | 0 | v1 cost telemetry; see tokens_in |
| `tokens_cache_read` | 0 | v1 cost telemetry; see tokens_in |
| `usage` | 0 | v1 cost telemetry; see tokens_in |
| `scope_breadth_ack` | 3 | v1 scope-breadth gate waiver; v2 has no such gate |
| `scope_breadth_ack_reason` | 3 | reason for a dropped v1 scope-breadth waiver |
| `no_scope_declared` | 0 | v1 scope gate waiver; v2 treats an empty scope as unscoped |
| `no_scope_declared_reason` | 0 | reason for a dropped v1 scope waiver |
| `scope_changes` | 10 | v1 scope audit trail; v2 records changes as field events going forward, the old trail stays in git history |
| `body_changes` | 1 | v1 body audit trail; the old trail stays in git history |
| `triage_changes` | 1 | v1 triage audit trail; the old trail stays in git history |
| `designated_repro_test` | 0 | v1 bug repro binding; v2 binds tests with `frob:tests` |
| `threat` | 0 | v1 security threat text; v2 keeps threats in the body |
| `anchor` | 0 | v1 anchor gate; no v2 equivalent |
| `anchor_reason` | 0 | reason for a dropped v1 anchor |
| `land_commit` | 0 | v1 land record; v2 derives the landing commit from git history |
| `findings` | 2 | v1 post-land sweep findings of dropped draft tickets; v1 gate output, not ticket data |

## Dropped behaviour

| What | Why |
|---|---|
| per-criterion acceptance evidence | criteria are imported with bound=false; the v1 evidence lines become `evidence` events whose `accepts` lists the criteria they were offered for |
| evidence transcripts | v1 stored only `cmd`, exit code and a 12-hex sha256 prefix; the digest field holds that prefix (not a blake3 hash) and no blob exists |
| state history | v1 keeps only the current state, so each ticket gets one `transition` to its final state; in-progress becomes todo (leases do not carry over) |
| real timestamps | v1 `created` has day granularity; all imported event times are synthetic offsets from it (see the module docs) |
