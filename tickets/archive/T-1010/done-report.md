## Done report

Changed:
src/frob/gates/_rule_id_scan.py (new)
src/frob/gates/_rule_id_scan.py::scan_emitted_rule_ids
src/frob/gates/_rule_id_scan.py::generated_gate_rule_ids
src/frob/gates/_rule_id_scan.py::SCANNED_BASES
src/frob/gates/_rule_id_scan.py::RETIRED_RULE_IDS
src/frob/gates/__init__.py::_KNOWN_GATE_RULES (header comment only; literal contents unchanged)
tests/test_gates.py::TestKnownGateRuleIds.test_every_emitted_rule_literal_is_known (rewritten as generator-freshness check)
tests/test_gates.py::TestKnownGateRuleIds.test_scan_finds_a_synthetic_rule_id (new)
tests/test_gates.py::TestKnownGateRuleIds.test_scan_resolves_const_name_reference (new)
tests/test_gates.py::TestKnownGateRuleIds.test_retired_id_stays_excluded (new)

Design chosen: checked-in generated literal, verified by drift-lock (not a
runtime cached scan). `_KNOWN_GATE_RULES` stays a plain `frozenset({...})`
literal in `frob.gates.__init__`; the T-0964 scan (rule="..."/rule=CONST_NAME
over src/frob/gates/**, src/frob/strata/**) is promoted into importable
`frob.gates._rule_id_scan.scan_emitted_rule_ids`/`generated_gate_rule_ids`,
and the drift-lock test now calls that production scanner instead of
duplicating it, asserting the checked-in literal is a superset of what the
scanner currently reports (mod RETIRED_RULE_IDS). Two concrete reasons
for not computing `_KNOWN_GATE_RULES = generated_gate_rule_ids(...)` at
import instead:
1. `frob.tickets._new_gate_rule_acceptance` reads that literal's SOURCE TEXT
   (via `git show` + regex, not import) for its own T-0756 close/land
   acceptance-policy preflight -- a computed expression has no literal text
   to scrape and would silently blind that consumer forever, in a file this
   ticket's scope does not cover to compensate.
2. Startup cost: `frob.gates` import stays "parse one frozenset literal,
   zero filesystem scanning" -- a cached-scan design would add an rglob +
   per-line regex pass to the first gate invocation of every `frob check`/
   `frob test` process for a set that changes a few times a month.
`RETIRED_RULE_IDS` (frozenset, currently empty) is the one hand-maintained
exclusion knob, living in `_rule_id_scan.py`, not the old test-local
`_KNOWN_ISSUE_ALLOWLIST` (retired).

Disclosed residual gap (v1, matching this repo's usual disclosed-not-
silently-dropped posture): the scan recognizes only the `rule="..."`/
`rule=CONST_NAME` construction shapes (the T-0964 class this ticket's
acceptance criterion names). It does NOT detect ids built via a bare
positional arg or dict-literal value (`frob.gates._secrets`'s `_pat(...)`
tuples, `frob.gates._arch`'s category dict, `frob.gates.
_registry_exhaustiveness`'s bare returns -- 23 ids currently: SEC001/SEC003,
REG001-003, ARCH001/101-103, and DUP001/002 + PERF001-009 which additionally
live outside SCANNED_BASES in src/frob/dup and src/frob/perf). These stay
hand-maintained in `_KNOWN_GATE_RULES` exactly as before this ticket;
documented in `_rule_id_scan.py`'s module docstring and `__init__.py`'s
`_KNOWN_GATE_RULES` header comment. Extending detection to those shapes is
real work outside this ticket's declared scope -- left as a candidate
follow-up rather than attempted half-heartedly here (not filed as a
separate ticket per instructions since it's a disclosed v1 scope note, not
a newly discovered defect).

Two COV001 waivers (SCANNED_BASES, RETIRED_RULE_IDS, scan_emitted_rule_ids,
generated_gate_rule_ids all carry one) instead of `frob:doc` anchors: a
`frob:doc docs/modules/gates.md#public-api` directive on the new symbols
pulls in SCOPE002's full closure over that monolithic shared doc file
(every OTHER symbol it describes across dozens of unrelated modules) --
wildly out of proportion to land four anchors. Reasoned and disclosed in
each waiver and in the module docstring.

Evidence:
tests/test_gates.py -q -- 786/786 pass (includes all 6
TestKnownGateRuleIds tests: 2 pre-existing accessor tests, the rewritten
generator-freshness drift-lock, and 3 new tests: a fresh rule="..." literal
is found with no hand edit, a rule=CONST_NAME reference resolves, and a
retired id is excluded from generated_gate_rule_ids()).
tests/test_tickets_new_gate_rule_acceptance.py -q -- 11/11 pass (T-0756
consumer parity: _KNOWN_GATE_RULES literal text scraping unaffected).
frob test --base main -- python exit=0, 4 outcomes recorded, PASS.
frob check --ticket T-1010 --only gates-fast/gates-native/gates-security --
all gate groups pass, 0 errors (chunked per playbook section 3b).
frob check --ticket T-1010 --only static -- passes (frob-exports advisory
for the new module is "pass" status, matches every other package's
baseline).
frob check --ticket T-1010 --only lint -- 0 errors after ruff format/fix on
touched files; remaining 1 warning is src/frob/gates/_docptr.py (untouched
by this ticket, pre-existing).

Filed: none (residual scan-shape gap disclosed above, not filed separately
per instructions' framing of it as this ticket's own v1 scope boundary).

Gates: frob check --ticket T-1010 clean across gates-fast/gates-native/
gates-security/static/lint (chunked, per playbook section 3b). Waivers:
COV001 x4 (doc-anchor scope-closure disproportion, reasoned above),
INV006 x1 (module-docstring design-rationale prose, same calibration as
frob.tickets._new_gate_rule_acceptance's own T-0756 INV006 waiver),
PERF004 x1 (per-SCANNED_BASES-entry distinct sort, not a shared re-sort).

### Changed
(no changed files detected)

### Evidence
- `tests/test_gates.py::TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestKnownGateRuleIds::test_scan_finds_a_synthetic_rule_id` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestKnownGateRuleIds::test_scan_resolves_const_name_reference` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestKnownGateRuleIds::test_retired_id_stays_excluded` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestKnownGateRuleIds::test_returns_known_rule_id` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestKnownGateRuleIds::test_is_frozenset` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 0 error(s), 19101 warning(s), 329 waived
- error-findings: none (measured, zero errors)
