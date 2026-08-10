---
id: T-1725
title: Hooks and docs reference frob verbs by name with nothing checking they resolve;
  gate it before the CLI regrouping renames them
state: done
kind: bug
origin: agent
created: '2026-08-07'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- .claude/hooks/frob-timeout-guard.py
- .claude/hooks/frob-suggest.py
- src/frob/gates/_wire.py
- docs/modules/gates.md
- src/frob/gates/_waive.py
- tests/test_gates.py
- src/frob/gates/_pii_structural/_keywords.py
- tickets/T-1725/ticket.md
- tickets/T-1725/done-report.md
- docs/design/registry/check-coverage.yaml
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_waive.py
  reason: WIRE003 registration in _KNOWN_GATE_RULES; the new gate's own regression
    tests
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tests/test_gates.py
  reason: WIRE003 registration in _KNOWN_GATE_RULES; the new gate's own regression
    tests
  actor: logan
  at: '2026-08-07'
- op: add
  glob: src/frob/gates/_pii_structural/_keywords.py
  reason: PII012 'token' homonym allowlist entries for the new WIRE003 identifiers;
    v2 ledger files
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tickets/T-1725/ticket.md
  reason: PII012 'token' homonym allowlist entries for the new WIRE003 identifiers;
    v2 ledger files
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tickets/T-1725/done-report.md
  reason: PII012 'token' homonym allowlist entries for the new WIRE003 identifiers;
    v2 ledger files
  actor: logan
  at: '2026-08-07'
- op: add
  glob: docs/design/registry/check-coverage.yaml
  reason: REG010 registry sync entry for the new CHK-GATE-WIRE003 self-audit id
  actor: logan
  at: '2026-08-07'
evidence:
- tests/test_gates.py::TestWireGate::test_wire003_matcher_pattern_stale_verb_is_flagged
- tests/test_gates.py::TestWireGate::test_wire003_suggestion_string_stale_verb_is_flagged
- tests/test_gates.py::TestWireGate::test_wire003_real_verbs_are_not_flagged
- tests/test_gates.py::TestWireGate::test_wire003_dotted_module_path_is_not_flagged
designated_repro_test: null
threat: null
component: null
---
The PreToolUse hooks in `.claude/hooks/` reference frob verbs BY NAME, as
plain strings, and nothing checks that those names resolve. The CLI
regrouping work (T-1567..T-1571) renames and regroups verbs. A rename will
silently break every reference, and the failure mode is the worst kind:
the hook keeps running and keeps passing.

Concrete references today:

- `frob-timeout-guard.py` matches `frob +(ticket +(land|done-report)|check|
  test)` to decide whether a command needs a large tool timeout. Rename or
  regroup any of those four and the guard stops firing -- silently. The
  stall pattern it exists to prevent comes straight back, and nothing says
  the guard went blind.
- `frob-suggest.py` SUGGESTS `uv run frob test`, `frob check`, `frob ticket
  ...`, `frob coverage`, `frob worktree` in its refusal text. After a
  rename these become instructions to run a command that no longer exists
  -- a hook that blocks a caller and then tells it to do something
  impossible, which is the T-1705 failure exactly.

Both are now git-tracked (`.claude/hooks/**`), so a gate can see them.

Two pieces of work:

1. A DETECTOR. A rule (register a real id in the catalog; do not invent an
   unregistered one) that extracts frob verb references from tracked hook
   sources and fails when one does not resolve against the live CLI
   dispatch table. Resolve against the DISPATCH TABLE, not a hand-written
   list of verb names -- a hand-written list is the same defect class as
   the bug, and it will drift the first time someone adds a verb.

   Both reference SHAPES must be covered: the regex/matcher form
   (`frob-timeout-guard`'s PATTERN) and the prose form inside suggestion
   strings. The second is easy to forget because it is "just a message",
   and it is precisely the half that misleads a human.

2. SEQUENCING. T-1567..T-1571 are blocked on this, deliberately. The
   detector has to exist BEFORE the renames, or the renames are exactly
   the event it cannot warn about. Landing it afterwards means hand-auditing
   the hooks and hoping.

Note for whoever does the regrouping afterwards: keeping the old verb as a
deprecated alias does NOT make this unnecessary. The hooks would keep
working while every suggestion string tells callers to use a verb the help
output no longer documents, which is drift with a longer fuse.

Wider scope, worth checking while here rather than filing again: the same
by-name coupling exists anywhere outside `src/` that names a frob verb --
`docs/guides/agent-playbook.md`, `docs/modules/cli.md`, the scaffold
templates, and any CI recipe. The detector should cover tracked
non-source references generally, not hooks specifically. Report what it
finds; the count is itself the argument for how bad the coupling is.

## Done report

New WIRE003 rule (`frob.gates._wire._wire003_stale_verb_references`)
resolves every `frob` verb reference in a tracked hook/doc against the
LIVE CLI dispatch table -- `frob.__main__._build_parser`, walked
recursively via `argparse._SubParsersAction.choices` -- never a
hand-written list of verb names, per the ticket's own explicit
instruction (a hand-written list is the same defect class as the bug).

Both named reference shapes are covered from one extraction path:
- The regex/matcher form: `.claude/hooks/frob-timeout-guard.py`'s own
  `PATTERN` (a raw string, never backtick-wrapped) is found via
  `ast.parse` locating `re.compile(...)` call arguments.
- The prose form: any backtick-quoted span, matching the convention
  `.claude/hooks/frob-suggest.py`'s own suggestion strings already use
  (`` `uv run frob test` ``, etc.) and markdown's own "this is code"
  marker.

Extended-glob alternation (`+()`/`|`) is split into independent
fragments before tokenizing, so `frob +(a|b)` correctly checks BOTH `a`
and `b`, not just the first branch. At most 2 leading tokens are read
per fragment (real `frob` commands never nest past `<verb> <subverb>`),
which also fixes the "T-0001 read as a fake verb" false positive a
naive unbounded token grab would produce on `frob ticket land T-0001`.

SEQUENCING (item 2, the ticket's own instruction): this lands before
T-1567..T-1571's CLI regrouping, as required -- the detector must exist
before the renames it is meant to catch, or it cannot warn about the
event that motivated it.

WIDER SCOPE (measured, as asked): a repo-wide `docs/**/*.md` scan
(backtick spans only) found 48 candidate references across 10 files;
including fenced code blocks (dropped from the shipped implementation)
raised that to 181 across many more files, dominated by fenced blocks
containing command OUTPUT (log lines, JSON, table rows) that reads as
command-shaped to this heuristic without being one, plus doc prose
using backtick-quoted vocabulary (ticket priority levels, board column
names) that happens to sit near the word "frob". This precision gap is
real and disclosed, not silently dropped: `_WIRE003_SCAN_GLOBS`'s own
docstring in `src/frob/gates/_wire.py` and the new "WIRE003 (T-1725)"
section in `docs/modules/gates.md` both state the measured counts and
name what a follow-up (a per-token allowlist, or a stricter anchor
requirement) would need before widening scope is safe at ERROR
severity -- forcing today's heuristic through repo-wide would reproduce
the 997-waiver anti-pattern this repo has already paid for once.

Registered as WIRE003 in `_KNOWN_GATE_RULES` (`frob.gates._waive`), per
the ticket's instruction to register a real id rather than inventing an
unregistered one.

PII012 note (same class as a recent T-1734 fix): the identifier
`_WIRE003_TOKEN_RE`/`token_match`/`token` triggered PII012's
name-signature sweep (matches the "credentials" category's "token"
keyword) -- added to the SAME `_PII012_REVIEWED_NON_PII` allowlist this
repo already uses for the identical homonym elsewhere (`_TYPE_TOKEN_RE`,
`_leaf_token`, etc. -- "a parsed lexical word," never an auth token),
rather than a second suppression style.

### Changed
```
 docs/modules/gates.md                       |  63 +++++++
 src/frob/gates/_pii_structural/_keywords.py |   6 +
 src/frob/gates/_waive.py                    |   6 +
 src/frob/gates/_wire.py                     | 251 +++++++++++++++++++++++++++-
 tests/test_gates.py                         |  99 +++++++++++
 tickets/T-1725/ticket.md                    |  43 ++++-
 6 files changed, 460 insertions(+), 8 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestWireGate::test_wire003_matcher_pattern_stale_verb_is_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestWireGate::test_wire003_suggestion_string_stale_verb_is_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestWireGate::test_wire003_real_verbs_are_not_flagged` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestWireGate::test_wire003_dotted_module_path_is_not_flagged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 0 error(s), 1412 warning(s), 726 waived
- error-findings: none (measured, zero errors)
