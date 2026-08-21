## Done report

Measured first (ticket's own suggested first step): of the 3 items in
docs/audits/docs-staleness-2026-07-29.md's "Non-python targets" section,
none are closed by work landed since filing. Specifically the ticket
body's own open item -- frob.toml severity claims in prose have no
anchor -- is still real and live: docs/modules/arch.md:57-58 claims
ARCH101/ARCH102 are `warning` while frob.toml's `[gates.severity]`
overrides both to `error` (confirmed by running the new gate below
against this repo's own tree). DOC006's kind 3 (CONFIG REFERENCE) only
resolves `[section.key]` EXISTENCE (`_config_path_exists`), never a
claimed VALUE -- confirmed by reading `src/frob/gates/_docptr.py`
directly, no value-comparison code path exists there.

Implemented: DOC013 (`docseverity_gate`,
src/frob/gates/_doclink_docanchor.py) -- scans every obligated/linked doc
for markdown severity-table rows shaped `` | `name` (CODE, ...) | ... |
SEVERITY_WORD | `` and flags a row whose `SEVERITY_WORD` contradicts an
explicit `frob.toml [gates.severity]` override for `CODE`. Deliberately
narrow per this repo's closed-set/mechanically-resolvable pointer
philosophy (this module's own docstring) and this repo's own
token/grammar-not-lexical standing directive: only the two doc words that
map 1:1 onto a real `frob.toml` value (`error`, `warning`/`warn`) are
compared; a softer word this repo's docs also use for a gate's
class-coded DEFAULT severity (`suggestion`, `report`) is never flagged,
since there is no independent default-severity registry to check it
against -- ambiguous vocabulary is silence, not a guess (verified by
`test_ambiguous_doc_word_is_never_flagged` and
`test_no_override_is_a_noop`). Ships at WARN (new-gate-at-WARN-first
precedent, T-0688), same posture DOC009/DOC012 shipped under before their
own later promotion to ERROR once burned down.

Wired: `src/frob/gates/__init__.py` (import, `_ALL_GATES`,
`_CANONICAL_GATE_ORDER`, `run_gates` lambda dispatch, `__all__`),
`src/frob/check/__init__.py` (`_STAGE_GROUPS["gates-fast"]` membership so
`--budget`/`--stamp-baseline` chunking do not silently skip it),
`docs/modules/gates.md` (new DOC013 table row).

Measured against this repo's own tree (`frob check --ticket T-2080 --only
docseverity`): 2 live WARN findings, both at the ticket body's own
motivating file (docs/modules/arch.md:57 ARCH101, :58 ARCH102). Filed
T-2766 (renumbers at land) to fix that content -- out of scope
for this ticket (docs/modules/arch.md is not in T-2080's declared scope).

Acceptance[2]/remaining items from the ticket body, not attempted here
(scoping decision, not an oversight):
- pyproject.toml entries / tmLanguage grammar lists / other non-Rust,
  non-Makefile config surfaces having no graph node at all: still open,
  genuinely separate mechanism work (a different pointer KIND, not a
  value-vs-claim check) -- left for a follow-up rather than folded into
  this leaf, since DOC013's grammar (markdown severity table + frob.toml
  override) does not generalize to it.
- Rust FILE::SYMBOL coverage sufficiency (T-1228): confirmed by reading
  `docs-staleness-2026-07-29.md`'s "Non-python targets" section itself --
  none of its 3 listed items are Rust file/symbol citations, so T-1228's
  existing coverage is orthogonal to this ticket's scope, not a
  denominator reduction for it.

Recommend narrowing T-2080 to closed (this leaf's own scope: the
frob.toml-severity-value anchor) rather than leaving it open for the
pyproject/tmLanguage item -- that item deserves its own ticket with its
own acceptance shape, not a reopened catch-all.

Filed: T-draft-104c5db0 (from T-2245, renumbered T-2764 at land --
unrelated native-staleness finding), T-2766 (docs/modules/
arch.md severity table fix)

Evidence: tests/test_gates.py::TestDocseverityGate::
test_mismatched_severity_row_fires_doc013,
test_matching_severity_row_passes, test_no_override_is_a_noop,
test_ambiguous_doc_word_is_never_flagged -- all 4 pass
(`uv run pytest tests/test_gates.py -k TestDocseverityGate`,
exitstatus=0 collected=4 failed=0).

Gates: `frob check --ticket T-2080 --only scope --only prework --only
docseverity --only gates_schema` clean (gate:DOC 0 errors 2 warnings --
the 2 warnings ARE the arch.md finding above, expected; gate:SCOPE 0
errors, 1061 pre-existing SCOPE002 under-capture warnings on
tests/test_gates.py's OTHER, unrelated test classes -- not introduced by
this change, tests/test_gates.py is a 10k+-line shared file). DRIFT/
claude-config-drift failures present in a full `frob check` run are
pre-existing and repo-wide, unrelated to this ticket.

### Changed
```
 tickets/T-2080/ticket.md           | 62 ++++++++++++++++++++++++++++++++++++--
 tickets/T-2766/ticket.md | 37 +++++++++++++++++++++++
 2 files changed, 97 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestDocseverityGate::test_mismatched_severity_row_fires_doc013` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDocseverityGate::test_matching_severity_row_passes` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDocseverityGate::test_no_override_is_a_noop` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestDocseverityGate::test_ambiguous_doc_word_is_never_flagged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 16 error(s), 1867 warning(s), 708 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1688, COV003@tickets/T-2365, CYCLE001@src/frob/__init__.py, DOC006@docs/audits/test005-zero-classification-t1418.md, DRIFT001@src/frob/_cli_parsers/_ticket/_new.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md
