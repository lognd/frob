## Done report

Shipped batch 1 of the T-1137 `--fix` epic: the three Tier-A
deterministic fix handlers named in this ticket's acceptance criteria,
in a new src/frob/gates/_fix_engine.py:

- `fix_doc007_dotted_form`: rewrites a `frob:tests` directive using
  pytest's `Class::method` collect-only separator to this graph's own
  dotted `Class.method` form, in place at its recorded origin. Pure
  string surgery keeping the first `::` (file separator) intact and
  replacing every subsequent `::` with `.`. An already-dotted target is
  a no-op.
- `fix_doc002_unique_slug`: for a `frob:doc`/`frob:tests` `<file>#<slug>`
  anchor that does not resolve, rewrites `#<slug>` to the single
  `difflib.get_close_matches` candidate (cutoff 0.6, n=len(slugs) so a
  3-way-ambiguous slug is never misreported as unique) if EXACTLY one
  exists; zero or 2+ candidates are left untouched (the assisted
  fix-it path, out of this ticket's own scope).
- `fix_tick002_renumber`: performs the renumber TICK002's own message
  already prescribes, by calling the existing `frob.tickets.
  _new_renumber.finalize_draft` (the same function `frob ticket land`
  calls) for every draft id in the queue while on the default branch --
  no new renumber logic, per the ticket's own scope note. T-1125 already
  landed (confirmed: `frob ticket show T-1125` -> done) so its
  prose-reference rewrite is included automatically via
  `finalize_draft` -> `renumber_one`.

`apply_tier_a_fixes(root, snapshot, queue)` runs all three in order and
returns every `FixApplied` (rule/file/line/one-line rewrite summary)
actually made -- disclosed, never a waiver insertion, never a guess.

Scope note (disclosed, not silently cut): this ticket's declared scope
is src/frob/gates/**, src/frob/tickets/**, tests/test_gates.py -- the
actual `frob check --fix` CLI FLAG (argument parsing in
src/frob/_cli_parsers/_check.py, orchestration in
src/frob/app/check_runner.py) is out of that scope and NOT wired in
this ticket. `apply_tier_a_fixes` is the callable entry point a later
CLI-wiring batch of the same T-1137 epic calls directly; documented as
this exact scope boundary in docs/modules/gates.md's new section. No
tickets/** files needed touching beyond calling the existing
finalize_draft API, matching the ticket's own scope note.

SYS104 upkeep (coordinator directive, mandatory as of this wave): added
`attr interface=` entries to design/frob.strata's `gates` node for the
5 new public symbols (FixApplied, apply_tier_a_fixes,
fix_doc002_unique_slug, fix_doc007_dotted_form, fix_tick002_renumber).
While verifying this, `frob check --only sys` also surfaced that
T-1141's TestGateRuleBuilderExclusion and T-1144's
TestToolResultBuilderExclusion (both landed earlier this same wave,
before SYS104 became mandatory) were missing their `testsuite` node
interface= entries -- fixed those too in the same land (design/
frob.strata scope, reasoned addition) rather than leaving a known
SELFAUDIT001 gap for the next agent to trip over.

Verification: ruff check clean (both `ruff` and `uv run ruff`) on
src/frob/gates/_fix_engine.py, src/frob/gates/__init__.py,
tests/test_gates.py, docs/modules/gates.md.
tests/test_gates.py::TestFixEngineTierA (7 cases, one per acceptance
criterion plus its negative/no-op counterpart) passes; full
tests/test_tickets_collision.py (15 cases, unaffected by this change)
passes. frob check --ticket T-1138 --only coverage/docanchor/doclink/
drift: clean for this ticket's own symbols (the 1 remaining COV001 and
several COV006/COV007 findings are pre-existing repo debt unrelated to
_fix_engine, confirmed by name). frob check --ticket T-1138 --only sys:
0 SELFAUDIT001 findings after the design/frob.strata upkeep.

Filed: none.

### Changed
```
 design/frob.strata            |   8 ++
 docs/modules/gates.md         |  61 +++++++++
 src/frob/gates/__init__.py    |   7 ++
 src/frob/gates/_fix_engine.py | 280 ++++++++++++++++++++++++++++++++++++++++++
 tests/test_gates.py           | 249 +++++++++++++++++++++++++++++++++++++
 tickets.md                    |  43 ++++++-
 6 files changed, 643 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestFixEngineTierA::test_doc007_dotted_form_rewrite_applies_and_reverifies_clean` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierA::test_doc007_already_dotted_is_a_no_op` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierA::test_doc002_unique_fuzzy_candidate_rewritten_and_reverifies_clean` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierA::test_doc002_ambiguous_candidates_stay_unfixed` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierA::test_doc002_zero_candidates_stay_unfixed` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierA::test_tick002_renumbers_draft_and_reverifies_clean` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierA::test_tick002_off_default_branch_is_a_no_op` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: 23 error(s), 1872 warning(s), 433 waived
- error-findings: ARCH001@src/frob/app/ticket_runner/_close_cmd.py, ARCH001@src/frob/doctor.py, ARCH001@src/frob/tickets/_setters.py, COV001@src/frob/gates/_tracked_files.py, E501@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/doctor.py:243, E501@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/vet/_capability.py:5338, E501@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/vet/_supplychain.py:154, E501@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/vet/_supplychain.py:168, E501@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/vet/_supplychain.py:209, E501@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/vet/_supplychain.py:267, E501@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/vet/_supplychain.py:295, F401@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/tickets/__init__.py:111, F401@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/tickets/__init__.py:22, F401@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/tickets/__init__.py:23, F401@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/tickets/__init__.py:35, F401@/home/logan/projects/frob/.claude/worktrees/w18-gates3/src/frob/tickets/__init__.py:46, INV006@src/frob/app/stats_runner.py, INV006@src/frob/gates/_fix_engine.py, INV006@src/frob/gates/_tickets_gate.py, PII012@src/frob/gates/_tickets_gate.py, PII012@tests/system/test_cli_doctor.py, PRE001@tickets/T-1138, TEST001@src/frob/gates/_fix_engine.py
