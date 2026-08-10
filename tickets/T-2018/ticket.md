---
id: T-2018
title: Symbolic attribution exists but is invisible where findings are reported, so
  agents attribute floor errors by unsound git-diff guessing
state: queued
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
scope_breadth_ack: false
scope_breadth_ack_reason: null
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
