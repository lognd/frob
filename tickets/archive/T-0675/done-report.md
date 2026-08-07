## Done report

Resolved RECONCILIATION.md finding (f) (compliance/secrets/pii leaf-
granularity gap, 599+56+44 = 699 leaf items) with an explicit decision:
freeze at unit granularity (option (b)), not build the leaf-level
registry (option (a)).

Rationale, recorded in three places so the decision is discoverable from
any of the three docs the finding touches:

1. docs/design/registry/RECONCILIATION.md finding (f) -- marked RESOLVED
   in its own heading, with the decision and why option (a) was rejected
   on the merits (most of the 599 compliance leaf counts are borrowed
   denominators from external standards -- GDPR articles, ASVS
   requirements, CIS safeguards, ISO 27002 controls -- with no per-leaf
   text sourced in-doc; minting one id per bare count would fabricate
   699 ids dressed as a real enumeration). Also records that this freeze
   was already made operationally by the three sibling reconciliation
   tickets T-0675 was blocked on (T-0386/T-0387/T-0388), each of which
   built its registry file at unit granularity with a passing
   file-specific EXHAUSTIVENESS meta-test.

2. docs/design/registry/README.md -- new "Granularity freeze (finding
   (f), T-0675)" section next to the file list, cross-referenced from
   the compliance.yaml/secrets.yaml/pii.yaml table rows.

3. docs/design/compliance-corpus.md and docs/design/secrets-pii-corpus.md
   -- a short paragraph directly under each source doc's own
   DENOMINATOR MANIFEST block, pointing at RECONCILIATION.md finding (f)
   for the full record, so a reader of the source doc itself sees the
   freeze decision at the point where the leaf-vs-unit tension is
   visible.

No registry yaml files were rebuilt or resized -- compliance.yaml (27),
secrets.yaml (3), pii.yaml (7) stay at their existing unit granularity
(37 entries total), matching what T-0386/T-0387/T-0388 already built and
closed. This is a docs-only ticket; no src/ changes were needed or made.

Verification: the three existing file-specific EXHAUSTIVENESS meta-test
files (test_registry_reconciliation_compliance.py,
test_registry_reconciliation_secrets.py, test_registry_reconciliation_pii.py)
still pass unchanged (23 passed) since no registry yaml content changed,
only prose/docs. Ran the full FROB_AGENT chunked --only loop scoped to
T-0675 (lint, static, gates-fast, gates-native, gates-security) -- all
pre-existing violations shown belong to files outside this ticket's
scope (src/frob/exports, src/frob/doctor.py, docs/guides/install.md,
etc., unrelated T-0858/older debt); zero new violations attributable to
the four docs files this ticket touched. `gate:REG` (registry
exhaustiveness) reports 0 errors both scoped (--only registry) and as
part of the gates-fast group.

This is a docs-only ticket with no pytest surface of its own (per the
agent playbook's documented precedent for such tickets): evidence is
bound to the existing CLI-dispatch integration test,
tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches,
observed collected and passing.

No out-of-scope discoveries were made; no draft tickets filed.

### Changed
```
 docs/design/compliance-corpus.md       | 10 +++++
 docs/design/registry/README.md         | 26 ++++++++++--
 docs/design/registry/RECONCILIATION.md | 27 +++++++++++-
 docs/design/secrets-pii-corpus.md      | 10 +++++
 tickets.md                             | 75 +++++++++++++++++++++++++++++++++-
 5 files changed, 142 insertions(+), 6 deletions(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
