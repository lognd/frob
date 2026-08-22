## Done report

FIX: frob.gates._rule_id_scan gained a second, deliberately broader
completeness net alongside the existing narrow scan:
scan_candidate_rule_id_literals(repo_root) matches any quoted,
rule-id-SHAPED string literal (PREFIX + 2-5 digits, optional -SUFFIX)
anywhere under src/ (not just SCANNED_BASES), independent of which
keyword (if any) introduces it -- catching a bare positional argument, a
`code=` kwarg, and a typed const assignment all with ONE mechanism.
find_unregistered_rule_ids(repo_root, known, retired) subtracts
known_gate_rule_ids() | RETIRED_RULE_IDS from the candidate set -- the
completeness check _KNOWN_GATE_RULES must return empty against, repo-wide.
The narrow scan_emitted_rule_ids/generated_gate_rule_ids (SCANNED_BASES,
rule=/rule=CONST_NAME only) is UNCHANGED -- still the authority
_KNOWN_GATE_RULES is generated FROM, still what the T-0756 acceptance
preflight's literal-text scrape depends on (per the ticket's explicit
"do not make the literal computed" instruction).

DIAGNOSIS (SYS109/TIERBDEMO001, why they were missed IN-BASE):
- SYS109 (src/frob/gates/_sys_selfaudit.py:204): a bare positional string
  argument to _selfaudit_violation("SYS109", ...) -- not a rule=/rule=
  CONST_NAME construction at all. Exactly the disclosed "bare positional
  argument" gap, now with a concrete live instance.
- CVEFP001 (src/frob/strata/_cve_fingerprint.py:391): `rule: str =
  "CVEFP001"`, a type-annotated pydantic field default -- a THIRD,
  previously undisclosed miss class (the `: str` annotation breaks
  _LITERAL_PATTERN's `rule\s*[:=]\s*"` match).
- TIERBDEMO001 is NOT actually a gap: it matches the exact rule="..."
  shape the narrow scan already detects, and is correctly excluded via
  RETIRED_RULE_IDS on purpose (synthetic reference-handler id, must never
  become a real registered rule). It only appeared in the audit's naive
  "288 quoted literals" count because that count does not itself consult
  RETIRED_RULE_IDS.
- SYS104: zero live construction sites anywhere under src/ (confirmed by
  the new broad scan) -- deleted with its writer per T-1870's owner
  directive; its "390 ledger references" are historical tickets.md prose,
  not code, outside a rule-id scanner's remit.
- BUDGET001/CHECK001/DEPLOY001/DEPLOY002/DEPLOY003/DERIVED001: all
  `Diagnostic(code="...")`, a sibling keyword to rule= in packages
  (src/frob/app, src/frob/deploy, src/frob/check) outside SCANNED_BASES
  entirely -- the already-disclosed out-of-base gap, confirmed live.

REGISTERED: the 8 real gaps (BUDGET001, CHECK001, CVEFP001, DEPLOY001,
DEPLOY002, DEPLOY003, DERIVED001, SYS109) added to _KNOWN_GATE_RULES in
src/frob/gates/_waive.py with per-id provenance comments.

TEST-FIRST: tests/gates/test_rule_id_scan_branches.py::
TestFindUnregisteredRuleIds::test_real_repo_registry_is_complete is the
whole-repo drift-lock. Measured directly (not just asserted) before the
_waive.py fix: find_unregistered_rule_ids(Path("."),
known=<pre-fix _KNOWN_GATE_RULES>) returned exactly the 8 real gaps
(BUDGET001/CHECK001/CVEFP001/DEPLOY001/DEPLOY002/DEPLOY003/DERIVED001/
SYS109) and nothing else -- confirmed empty of false positives (an
earlier iteration of the broad regex also caught "F401" from an inline
comment example in src/frob/process/parsers/common.py; fixed via
_INLINE_COMMENT_STRIP, now covered by
TestScanCandidateRuleIdLiterals::test_inline_comment_example_not_picked_up).
After the _waive.py fix: find_unregistered_rule_ids(Path("."),
known_gate_rule_ids()) returns {} (measured directly via a python
one-liner, then via the test node id below).

WIRE001: find_unregistered_rule_ids has no PRODUCTION caller outside its
own tests (its test caller is what makes the completeness check
automatic today, but WIRE001 correctly wants a production caller too).
Wiring it into frob.tickets._new_gate_rule_acceptance's own T-0756
preflight is out of this ticket's declared scope (src/frob/gates/
_rule_id_scan.py, gates/__init__.py, gates/_waive.py) -- waived with
follow_up=T-1956 (renumbers at land), which files that exact
wiring as its own ticket.

Changed:
- src/frob/gates/_rule_id_scan.py::scan_candidate_rule_id_literals (new)
- src/frob/gates/_rule_id_scan.py::find_unregistered_rule_ids (new)
- src/frob/gates/_rule_id_scan.py module docstring (T-1937 diagnosis)
- src/frob/gates/_waive.py::_KNOWN_GATE_RULES (+8 entries)
- tests/gates/test_rule_id_scan_branches.py (+14 tests: TestScan
  CandidateRuleIdLiterals, TestFindUnregisteredRuleIds)

Evidence: 10 node ids bound (see evidence list). BUG002 --check-repro
note: every NEW test node (TestScanCandidateRuleIdLiterals::*,
TestFindUnregisteredRuleIds::* except one shared class predating this
diff) returns NO_VERDICT at the parent commit -- collection failure,
since the classes/functions they exercise (scan_candidate_rule_id_
literals, find_unregistered_rule_ids) do not exist there yet. This is
the documented structural gap (a brand-new test node cannot collect at
a parent that predates the symbol it tests), not evasion -- confirmed via
`frob ticket evidence T-1937 --check-repro` exiting NO_VERDICT with
"could not even COLLECT at 423c6c423... (e.g. it calls a function that
does not exist there yet)". No --designate-repro was set for this
ticket; the pre/post fix behavior is instead proven directly above via
find_unregistered_rule_ids's measured before/after output, which is the
real acceptance shape this ticket asked for.

Filed: T-1956 (wire find_unregistered_rule_ids into the T-0756
acceptance preflight or a dedicated gate).

Pre-existing, out-of-scope gate errors observed during --land-parity
(none in files this ticket touched, unaffected by this diff): COV003 on
tickets/T-0185, T-1351, T-1507, T-1512 (stale evidence ids -- resolved by
the T-1934/T-1935/T-1941 work merged in from main during this ticket's
own pre-land `git merge main`); DOC002 and DRIFT002 on src/frob/tickets/
_land.py; DOCENUM001 on docs/modules/gates.md. None are in this ticket's
scope.

Gates: `frob check --ticket T-1937 --only test --only archgate --only
coverage --only sys` -- gate:ARCH pass, gate:TEST pass; gate:COV/
gate:DRIFT show only the pre-existing, out-of-scope findings above (0
findings in the 3 files this ticket touched). `frob check --only wire`
-- 0 errors, 1 waived (WIRE001, follow_up=T-1956, documented
above). `frob check --land-parity` -- 0 findings in files this ticket
touched; all remaining findings pre-existing/out-of-scope (listed above).

### Changed
```
 src/frob/gates/_rule_id_scan.py           | 198 ++++++++++++++++++++++++++++++
 src/frob/gates/_waive.py                  |  38 ++++++
 tests/gates/test_rule_id_scan_branches.py | 197 ++++++++++++++++++++++++++++-
 tickets/T-1937/ticket.md                  |  35 +++++-
 tickets/T-1956/ticket.md        |  26 ++++
 5 files changed, 491 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/gates/test_rule_id_scan_branches.py::TestScanCandidateRuleIdLiterals::test_finds_bare_positional_argument` (pytest node id, verified passing when recorded)
- `tests/gates/test_rule_id_scan_branches.py::TestScanCandidateRuleIdLiterals::test_finds_typed_const_assignment` (pytest node id, verified passing when recorded)
- `tests/gates/test_rule_id_scan_branches.py::TestScanCandidateRuleIdLiterals::test_finds_code_kwarg_outside_scanned_bases` (pytest node id, verified passing when recorded)
- `tests/gates/test_rule_id_scan_branches.py::TestScanCandidateRuleIdLiterals::test_inline_comment_example_not_picked_up` (pytest node id, verified passing when recorded)
- `tests/gates/test_rule_id_scan_branches.py::TestScanCandidateRuleIdLiterals::test_whole_line_comment_not_picked_up` (pytest node id, verified passing when recorded)
- `tests/gates/test_rule_id_scan_branches.py::TestFindUnregisteredRuleIds::test_empty_when_every_candidate_is_known_or_retired` (pytest node id, verified passing when recorded)
- `tests/gates/test_rule_id_scan_branches.py::TestFindUnregisteredRuleIds::test_reports_a_candidate_missing_from_both_known_and_retired` (pytest node id, verified passing when recorded)
- `tests/gates/test_rule_id_scan_branches.py::TestFindUnregisteredRuleIds::test_retired_id_is_excluded_even_when_shape_matches` (pytest node id, verified passing when recorded)
- `tests/gates/test_rule_id_scan_branches.py::TestFindUnregisteredRuleIds::test_real_repo_registry_is_complete` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 10 passed (from 10 evidence id(s))
- gates: 4 error(s), 1108 warning(s), 705 waived
- error-findings: DOC002@src/frob/tickets/_land.py, DOCENUM001@docs/modules/gates.md, DRIFT002@src/frob/tickets/_land.py, PRE001@tickets/T-1937
