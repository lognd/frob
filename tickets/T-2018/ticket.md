---
id: T-2018
title: Symbolic attribution exists but is invisible where findings are reported, so
  agents attribute floor errors by unsound git-diff guessing
state: done
kind: bug
origin: agent
created: '2026-08-10'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/verify/_attribution.py
- src/frob/gitio.py
- src/frob/app/verify_runner.py
- tests/unit/verify/test_attribution.py
- docs/modules/testing.md
- src/frob/verify/__init__.py
- tests/unit/verify/test_verify_runner.py
- tests/test_gitio.py
- rapid-debt.jsonl
- tickets/T-2010/ticket.md
- tickets/T-2010/done-report.md
- design/frob.strata
- docs/design/registry/capability-via-ratchet.lock.json
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/gitio.py
  reason: ad-hoc candidate-commit batch construction needs a commit-relative diff
    helper in gitio.py, wired into verify explain's existing refusal path
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/app/verify_runner.py
  reason: ad-hoc candidate-commit batch construction needs a commit-relative diff
    helper in gitio.py, wired into verify explain's existing refusal path
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/unit/verify/test_attribution.py
  reason: ad-hoc candidate-commit batch construction needs a commit-relative diff
    helper in gitio.py, wired into verify explain's existing refusal path
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/unit/test_gitio.py
  reason: ad-hoc candidate-commit batch construction needs a commit-relative diff
    helper in gitio.py, wired into verify explain's existing refusal path
  actor: logan
  at: '2026-08-10'
- op: add
  glob: docs/modules/testing.md
  reason: frob:doc anchor for the new gitio commit_diff helper
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/verify/__init__.py
  reason: export build_ad_hoc_batch so verify_runner.py can import it via the package's
    normal frob.verify surface
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/unit/verify/test_verify_runner.py
  reason: unit coverage for _run_explain/_explain_batch's ad-hoc fallback
  actor: logan
  at: '2026-08-10'
- op: remove
  glob: tests/unit/test_gitio.py
  reason: fix path typo -- the real gitio test file is tests/test_gitio.py, not tests/unit/test_gitio.py
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/test_gitio.py
  reason: fix path typo -- the real gitio test file is tests/test_gitio.py, not tests/unit/test_gitio.py
  actor: logan
  at: '2026-08-10'
- op: add
  glob: rapid-debt.jsonl
  reason: pre-existing land noise from this worktree series showing in the ticket-start
    diff range
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tickets/T-2010/ticket.md
  reason: pre-existing land noise from this worktree series showing in the ticket-start
    diff range
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tickets/T-2010/done-report.md
  reason: pre-existing land noise from this worktree series showing in the ticket-start
    diff range
  actor: logan
  at: '2026-08-10'
- op: add
  glob: design/frob.strata
  reason: new test file's subprocess/write_text capability sites need registering
    in the testsuite node's exec/fs.write via-lists
  actor: logan
  at: '2026-08-10'
- op: add
  glob: docs/design/registry/capability-via-ratchet.lock.json
  reason: bump SYS111 ratchet ceiling for the one new exec + fs.write test site
  actor: logan
  at: '2026-08-10'
evidence:
- tests/test_gitio.py::TestCommitDiff::test_single_commit_reports_its_own_hunk
- tests/test_gitio.py::TestCommitDiff::test_root_commit_has_no_parent_is_an_error
- tests/test_gitio.py::TestRecentCommits::test_since_none_returns_limit_bounded_recent_commits
- tests/test_gitio.py::TestRecentCommits::test_since_a_sha_returns_only_commits_after_it
- tests/unit/verify/test_attribution.py::TestBuildAdHocBatch::test_covers_a_commit_the_persisted_queue_never_saw
- tests/unit/verify/test_attribution.py::TestBuildAdHocBatch::test_end_to_end_attributes_through_attribute_batch
- tests/unit/verify/test_attribution.py::TestBuildAdHocBatch::test_commit_touching_no_resolvable_symbol_is_omitted
- tests/unit/verify/test_attribution.py::TestBuildAdHocBatch::test_since_bounds_the_candidate_range
- tests/unit/verify/test_attribution.py::TestBuildAdHocBatch::test_ambiguous_two_commits_reach_the_same_symbol_is_unattributed
- tests/unit/verify/test_attribution.py::TestBuildAdHocBatch::test_unreadable_git_history_degrades_to_empty_batch
- tests/unit/verify/test_attribution.py::TestLoadAttributionContext::test_returns_a_usable_snapshot_and_call_graph
- tests/unit/verify/test_attribution.py::TestLoadAttributionContext::test_build_failure_is_graph_unavailable
- tests/unit/verify/test_verify_runner.py::TestRunExplainAdHocFallback::test_empty_persisted_queue_still_attributes_via_ad_hoc_history
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
MEASURED 2026-08-10. T-1690 shipped a real symbolic-attribution engine
(`src/frob/verify/_attribution.py`: `attribute_batch`, reachability via
`frob.graph.callgraph.build_reference_graph`, never a path-string
comparison, ambiguity recorded as `status="unattributed"` with every
candidate sha, full audit trail logged). `frob verify` exposes it --
`src/frob/_cli_parsers/_verify.py:37` offers "print the attribution
reachability path for one finding".

IT IS NOT REACHING THE PEOPLE WHO NEED IT. In one session, THREE separate
agents attributed floor errors by hand, by guessing, and none invoked the
attribution engine:

- Agent A, on `COV003` for T-0907's evidence: "both from other agents'
  concurrent lands, confirmed via `git diff main --stat` on my own branch".
  WRONG. The coordinator traced it to T-1963's own land (`11c3c824f`),
  which renamed the bound test
  (`test_repair_refuses_loudly_...` -> `test_repair_recovers_even_...`).
  The method used -- "the file is not in my diff, therefore not mine" --
  cannot see an evidence binding broken by a rename.
- Agent B, on `ARCH001`/`REL002`/`AFFECT001`: "confirmed as a *different*
  concurrent agent's own `_fix_engine_sync.py` land, zero relation to my
  touched files". Correct answer, arrived at by the same unsound method.
- Agent C, on 105 `DSL001` findings: attributed them to pre-existing debt
  using `git blame` dates. Also wrong -- blame dates the TEXT, not the
  finding.

The common shape: every agent needs to answer "did MY land cause this?"
at least once per ticket, all of them answer it with ad-hoc git commands,
and the answers are unreliable in exactly the cases that matter (renames,
loudness changes, evidence bindings -- anything where the causing diff does
not textually contain the flagged line).

WHY THE COMMAND DID NOT HELP: it is a command. Per the standing directive,
"a command requires KNOWLEDGE of the command" -- and nothing in the gate
output, the land refusal, or the floor measurement mentions that attribution
exists. An agent measuring the floor sees a finding and a file:line, with no
hint that the repo can tell it who caused it.

## Do not fix it this way
- Do NOT fix this by adding the command to the agent playbook or a dispatch
  brief. That is precisely the intervention that already failed four times
  for `--check-repro` (T-1929), and it is a rule, not an enforcement.
- Do NOT run full attribution on every `frob check`. Attribution needs a
  call graph and a batch of candidate commits; making the default gate run
  pay for that would regress the measurement everyone runs constantly.
  Attribution should be offered/attached where a finding is REPORTED as new
  or as a regression, not for every finding on every run.
- Do NOT have it guess when reachability is ambiguous. T-1690 deliberately
  records `unattributed` with all candidate shas rather than picking the
  newest commit; preserve that. An honest "unattributed, candidates X/Y" is
  the useful answer -- a confident wrong attribution is what this ticket
  exists to stop.
- Do NOT duplicate the engine. `attribute_batch` exists and works; this is
  a surfacing problem, not an algorithm problem.

## Acceptance criteria
1. A test that FAILS FIRST: reproduce the T-0907 case -- a land that renames
   a test bound as evidence elsewhere -- and assert that the current
   regression/floor reporting gives the operator NO attribution for the
   resulting COV003. Then assert the attributed commit is named in the
   output the operator already reads.
2. Attribution appears where the finding is already surfaced, with no new
   verb required to obtain it.
3. Measured cost: report the added wall-clock on the surfaced path, and
   confirm the ordinary `frob check --only gates` run is unchanged.
4. An ambiguous case still reports `unattributed` with candidate shas, not
   a guess -- assert this explicitly.

## Note (T-1969's agent, 2026-08-10): a related UX gap in `frob verify explain`

While dropping T-2008 (re-measured, did not reproduce), I used `frob
verify explain "SELFAUDIT001:design"` per the standing method note to
confirm the finding was genuinely gone rather than guessing from a diff.
It returned `verify explain: verify queue is empty, nothing to attribute
against` (exit 1). That was the correct outcome here -- there was no
live finding to attribute -- but the message does not distinguish that
case from other reasons the queue could be empty (never populated,
already drained by someone else, a genuine tool/spawn failure). An agent
reading only the exit code and message cannot tell "the finding is
resolved" apart from "attribution is unavailable right now" -- the same
false-confidence shape this ticket is about, one layer earlier: the
signal that answers "should I trust this absence?" is itself ambiguous.
Worth folding into this ticket's acceptance work rather than filing a
duplicate: an empty-queue `explain` response should say which case fired
(or attach whatever queue-state fact would let the caller tell the
difference), not just "empty".