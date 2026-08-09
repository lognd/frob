## Done report

Changed:
- docs/design/registry/check-coverage.yaml: removed the stale
  CHK-GATE-SYS104 entry (gate_rule_entries) and decremented
  gate_rule_total from 293 to 292.

Root cause: T-1870 deleted the SYS104 gate rule (the interface=
mirror-conformance check) per an explicit owner directive, and its own
code comment (src/frob/strata/_selfconform.py:1770-1776) documents that
the CHK-GATE-SYS104 registry entry was supposed to be removed in the
same change -- but the entry survived in check-coverage.yaml, still
dispositioned `handled_by:SYS104` against a rule id no longer present
in the live gate/policy registry. This is a genuine defect (a doc/code
edge left out of a landed change), not pre-existing residue the
baseline had simply not recorded: reproduced directly with `uv run
frob check --only registry` on the pre-fix tree (REG002 error on
docs/design/registry/check-coverage.yaml) and confirmed unattributed
sweep origin matches (T-1870's own SYS104 removal, though the sweep
found it "unattributed" because T-1870 landed before the rolling
baseline existed).

Evidence -- a genuine (not confirmatory-only) regression test:
tests/test_check_coverage_registry.py::TestCheckCoverageRegistryFile::test_gate_rule_entries_match_live_known_rules
Verified BUG002-style: checked out the pre-fix check-coverage.yaml
(git show HEAD~1's content) into the working tree and re-ran this one
test node -- it FAILED (`assert 293 == 292`, comparing entry count
against known_gate_rule_ids()); restored the fix and it PASSES. This
directly reproduces and kills the defect, not a pre-existing-pass
confirmatory test.

Filed: none (no out-of-scope work found)

Gates: `uv run frob check --only registry` clean for this file (0
errors after fix, REG002 finding gone; 6 pre-existing REG008/REG011
warnings on other unrelated registry entries remain untouched, out of
this ticket's scope).

### Changed
```
 docs/commands/refactor.md                |  5 +-
 docs/design/registry/check-coverage.yaml |  7 +--
 rapid-debt.jsonl                         |  2 +
 src/frob/refactor/_verify.py             | 82 ++++++++++++++++++--------------
 tickets/T-1888/ticket.md                 |  2 +-
 tickets/T-1889/done-report.md            | 50 +++++++++++++++++++
 tickets/T-1889/ticket.md                 | 25 +++++++++-
 7 files changed, 128 insertions(+), 45 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 0 error(s), 773 warning(s), 692 waived
- error-findings: none (measured, zero errors)
