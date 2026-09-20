---
id: T-0401
title: 'AUDIT: strata vacuous-proof closure -- bind proofs to code, fail-closed on
  incompleteness (docs/audits/strata.md)'
state: done
kind: security
origin: human
created: '2026-07-20'
priority: medium
parent: T-0397
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/strata/
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: condense CWE-94 eval-join rationale into T-0401 body
  actor: logan
  at: '2026-09-19'
  old_length: 632
  new_length: 1582
- mode: append
  reason: condense CWE-78 eval-join rationale into T-0401 body
  actor: logan
  at: '2026-09-19'
  old_length: 1582
  new_length: 2551
evidence:
- tests/unit/strata/test_threat.py::TestEvalFiresCwe94::test_eval_capability_is_classified_not_benign_excused
- tests/unit/strata/test_threat.py::TestEvalFiresCwe94::test_eval_capability_fires_a_real_cwe94_obligation
- tests/unit/strata/test_threat.py::TestEvalFiresCwe94::test_eval_capability_discharges_with_a_real_mitigation_claim
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
See docs/audits/strata.md. HIGH: boundaries never bound to code (discharge = typing a matching string); vacuous discharge when foreign->sink flow is un-modeled (incomplete .strata discharges real caps); eval globally BenignCapability-excused (no RCE obligation); FOREIGN files loose under src/frob/ escape all SYS + THREAT004/005; utility flow marker defeats confidentiality noflow. RIGHT-WAY fix: join Boundary predicates against observed code; require flow-completeness before a NoFlow discharges (fail-closed); add eval obligation; make sys rules cover every capability-bearing file. Then re-audit until empty. G6-G12 in the doc.

<!-- narrative-moved:src/frob/strata/_threat_catalog_cwe.py:205:T-0401 -->
T-0401 (docs/audits/strata.md G3): `eval` was globally
`BenignCapability`-excused with the reason "no CWE_CATALOG entry
targets dynamic code evaluation as a sink" -- false; CWE-94 IS
exactly that entry, it was simply never joined to the `eval`
capability kind (only to `exec`). A SECOND `WeaknessEntry` row
sharing CWE-94's id but a different `capability_kind` is the SAME
multi-kind-per-weakness convention `capability_kind="sql"` already
uses twice (`CWE-89` above, `CWE-639`/`QUALITY_CATALOG`'s own `sql`
entry) -- `_entries_by_capability_kind` keys by kind, not id, so both
rows correctly fire the identical `weakness:CWE-94:<node>` discharge
obligation (one Claim satisfies both firings). Dropping the benign
excuse means a node/file with dynamic `eval`/`compile`/`__import__`
now fires a REAL, dischargeable THREAT002/THREAT003 obligation
instead of passing silently.

<!-- narrative-moved:src/frob/strata/_threat_catalog_cwe.py:47:T-0401 -->
T-0401 (docs/audits/strata.md G3): `eval` was globally
`BenignCapability`-excused with the (false) reason "no CWE_CATALOG
entry targets dynamic code evaluation" -- `CWE_TOP_25_CATALOG`'s
CWE-94 IS that entry (joined to `eval` there too, same section), but
`owasp-top-10` (this catalog, `VIEWS`) does not include CWE-94 at all
(G6: the default security view is narrower than cwe-top-25, a
SEPARATE disclosed gap, not fixed here). So `eval` also needs a join
WITHIN this catalog's own vocabulary for THREAT002 to classify it
under the default view -- CWE-78 is the closest existing id (a code-
execution sink, same "kernel model does not distinguish an OS-command
sink from a code-eval sink" reasoning CWE-94's own `exec` join already
uses), so a second row shares its id with a different
`capability_kind`, the SAME multi-kind-per-weakness convention
CWE-89/CWE-639 already establish for `sql`.