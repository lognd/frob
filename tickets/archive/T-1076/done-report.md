## Done report

Partial land of T-1076 (T-1072/T-0989 pattern, second file in this ticket
after the earlier _pii_structural split, commits aef72029/e9f49bd6).

Split src/frob/__main__.py (2615 lines) into a src/frob/_cli_parsers/
package: 79 `_add_*_parser` argparse builder functions, grouped into
_core.py (core analysis subcommands), _check.py (`frob check`'s own
flag groups), _reporting.py (gitlog/graph/ack/debt/deprecated/pool/
registry/fleet), _ticket.py (the full `frob ticket` subtree), and
_misc.py (test/vet/perf/release/mutate/stats/doctor/clean/fmt/natives/
serve/sys/deploy) -- largest new file is 937 lines. `__main__.py` itself
now holds only the entry point, `_SuggestingArgumentParser`/`_did_you_
mean`/`_closest`/`_collect_option_strings`, `_build_parser`, `_frob_
version`, `main`, and `_dispatch` (309 lines), importing every builder
name from the new package so the module's public surface (`_build_
parser`, `main`, `_add_test_parser`, etc, all imported directly by
tests) is unchanged. No cross-file calls existed between the five new
files (verified via grep before splitting) -- a purely mechanical
regrouping, no behavior change. Verified with `uv run python -c
"from frob.__main__ import _build_parser; _build_parser()"` plus
targeted pytest runs (tests/unit/test_main_entry.py full pass,
tests/test_gates.py::TestCoverageGate::
test_cov003_remediation_hint_names_no_nonexistent_flag,
tests/test_docptr_gate.py full pass, tests/test_tickets_acceptance.py
full pass, tests/test_ticket_land.py::TestSkipMutationEvidenceCliWiring
full pass, tests/integration/test_interfaces.py::TestInterfaces::
test_main_cli_dispatches) and a repo-wide `pytest --collect-only`
(clean, no collection errors).

Fixed the resulting DRIFT002 findings by updating the doc anchors in
docs/commands/check.md, docs/commands/exports.md, docs/commands/
scaffold.md, docs/guides/agentic-workflow.md, docs/guides/install.md to
point at the new `src/frob/_cli_parsers/*.py::_add_*_parser` locations.
Carried the original T-0585 INV006 waiver (the module's help-string
"only" language, not a real exclusivity contract) onto each of the five
new files with the same reasoning, since a per-file INV006 scan no
longer sees the single old waiver. Added `src/frob/_cli_parsers/**` to
the `cli` node's `code=` glob in `design/frob.strata` (SELFAUDIT001
fix) and touched its shared affects()-closure doc,
docs/strata/roadmap.md, with a one-line note (AFFECT001).

Also repaired a scope gap the predecessor's earlier _pii_structural.py
split (this ticket's first commit, aef72029/e9f49bd6) left behind: its
scope glob still named the old single file
(`src/frob/gates/_pii_structural.py`), which no longer matches the
package directory it split into -- added
`src/frob/gates/_pii_structural/**`, `docs/modules/gates.md`, and
`tests/test_pii_structural_gate.py` to scope so `frob check --ticket
T-1076` actually sees that package again (was silently SCOPE001-invisible
before this fix).

`frob check --ticket T-1076` now reports 12 errors, all pre-existing
debt this session did not introduce and is not fixing under this file's
work: 10 are DUP001/INV006/PERF001 findings inside the predecessor's
_pii_structural split (tests/test_pii_structural_gate.py duplicate test
bodies, `_dotted_prefix`/`_ts_string_literal_text` near-duplicates
against sibling gate modules, four files' inherited "only" help-text
missing a per-file INV006 waiver) that only became visible once the
scope glob was repaired above -- disclosed here, not silently fixed,
since fixing them is a distinct unit of work from the __main__.py
split this Done report covers. The remaining 2 (docs/modules/strata.md
INV003/INV004, src/frob/arch/_ffi.py PERF008) are unrelated pre-existing
repo debt outside T-1076's scope entirely (confirmed via `frob check
--ticket T-1076 --only scope` returning 0 errors) -- `frob check
--ticket` runs several gates repo-wide regardless of declared scope, so
they surface here without being this ticket's responsibility.
`ruff-format` also flags one unrelated pre-existing file
(src/frob/gates/_waive.py, untouched by this session).

Remaining T-1076 tier-2 files (dup/_pipeline.py 2628, ticket_runner.py
3957, tickets/__init__.py 4260, tickets/_land.py 4762) are untouched --
filed as a remainder draft (T-1086, see Filed below) rather
than attempted in this budget. Landing this file's split as a coherent
partial per this ticket's own acceptance framing (large-file is
unwaivable; a not-yet-decomposed file must say so explicitly, not
silently skip -- recorded here and in the remainder ticket, and the
predecessor's own leftover DUP/INV/PERF debt disclosed above rather
than silently absorbed into this file's own claim of done).

### Changed
```
 docs/commands/check.md                             |   10 +-
 docs/commands/exports.md                           |    2 +-
 docs/commands/scaffold.md                          |    2 +-
 docs/guides/agentic-workflow.md                    |   18 +-
 docs/guides/install.md                             |    2 +-
 docs/modules/gates.md                              |   19 +-
 src/frob/__main__.py                               | 2382 +-------------------
 src/frob/_cli_parsers/__init__.py                  |  180 ++
 src/frob/_cli_parsers/_check.py                    |  160 ++
 src/frob/_cli_parsers/_core.py                     |  447 ++++
 src/frob/_cli_parsers/_misc.py                     |  587 +++++
 src/frob/_cli_parsers/_reporting.py                |  272 +++
 src/frob/_cli_parsers/_ticket.py                   |  941 ++++++++
 src/frob/gates/_pii_structural.py                  | 2177 ------------------
 src/frob/gates/_pii_structural/__init__.py         |  267 +++
 src/frob/gates/_pii_structural/_crosslang.py       |  421 ++++
 .../gates/_pii_structural/_declared_surface.py     |   91 +
 src/frob/gates/_pii_structural/_emails.py          |  150 ++
 src/frob/gates/_pii_structural/_env_access.py      |  148 ++
 src/frob/gates/_pii_structural/_keywords.py        |  448 ++++
 src/frob/gates/_pii_structural/_python_fields.py   |  317 +++
 src/frob/gates/_pii_structural/_self_match.py      |   83 +
 src/frob/gates/_pii_structural/_signatures.py      |  361 +++
 src/frob/gates/_pii_structural/_tracked.py         |   41 +
 tests/test_pii_structural_gate.py                  |   54 +-
 tickets.md                                         |  285 ++-
 26 files changed, 5291 insertions(+), 4574 deletions(-)
```

### Evidence
- `tests/unit/test_main_entry.py::TestMainSigint::test_keyboard_interrupt_prints_clean_message_and_exits_130` (pytest node id, verified passing when recorded)
- `tests/unit/test_main_entry.py::TestMainSigint::test_normal_dispatch_is_unaffected` (pytest node id, verified passing when recorded)
- `tests/unit/test_main_entry.py::TestDidYouMean::test_unknown_subcommand_suggests_closest` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestCoverageGate::test_cov003_remediation_hint_names_no_nonexistent_flag` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestSkipMutationEvidenceCliWiring::test_flag_parses_to_true` (pytest node id, verified passing when recorded)
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 8 error(s), 1723 warning(s), 419 waived
- error-findings: DUP001@src/frob/gates/_pii_structural/_crosslang.py, DUP001@src/frob/gates/_pii_structural/_env_access.py, DUP001@tests/test_pii_structural_gate.py, INV006@src/frob/gates/_pii_structural/_declared_surface.py, INV006@src/frob/gates/_pii_structural/_emails.py, INV006@src/frob/gates/_pii_structural/_keywords.py, INV006@src/frob/gates/_pii_structural/_signatures.py, PERF001@tests/test_pii_structural_gate.py
