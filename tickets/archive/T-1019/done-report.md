## Done report

Re-measured before starting: `frob check --only registry --json` -> REG011
count 1157 (unchanged from the ticket's filing distribution: weaknesses.yaml
798, patterns.yaml 346, compliance.yaml 10, supply-chain.yaml 2,
secrets.yaml 1 -- confirmed by parsing every registry entry's disposition
via `frob.registry._models.parse_disposition` directly, not just the gate
diagnostic count, cross-checked file-by-file).

Clustering: extracted every OUT_OF_SCOPE entry's raw reason text per file
and counted DISTINCT strings -- the whole 1157-entry failing set reduces to
exactly 27 distinct reason strings (21 in weaknesses.yaml, 1 in
patterns.yaml, 2 in compliance.yaml, 2 in supply-chain.yaml, 1 in
secrets.yaml), each an exact-match slug/short-phrase already functioning
as a de-facto class label (e.g. "generic-precondition-model",
"crypto-primitive-model", "memory-model" for weaknesses.yaml CWEs;
"advisory-design-pattern-recommendation" for all 346 patterns.yaml
entries). This made the rewrite exact-string-keyed rather than freehand
per-entry: one substantive reasoned-none template was written per distinct
class, explaining (a) WHY frob cannot statically check that class and (b)
what layer, if any, could -- e.g. "sink-classification-model" ->
"none -- this CWE names a class of dangerous data SINK (a taint-tracking/
dataflow classification, not an AST-local pattern); frob's checkers are
structural/AST-level and do not perform interprocedural taint analysis --
a dedicated dataflow/taint analyzer is the layer that could catch this,
not frob today". secrets.yaml's single entry already carried a substantive
explanation (an external-tools bibliographic citation) -- kept verbatim,
only the `none -- ` marker was added, preserving its existing nuance
exactly as instructed.

Applied via a scripted exact-string replace (not yaml.dump re-serialization,
to avoid reordering/reformatting anything outside the touched field) --
verified afterward: `git diff --stat` on the 5 registry files shows EXACTLY
1157 insertions / 1157 deletions, one changed line per failing entry, no
other line touched. Every file re-parses cleanly with `yaml.safe_load`
after the rewrite.

Per-file before -> after REG011 counts (measured via `frob check --only
registry --json`, filtered to code=="REG011"):
- weaknesses.yaml: 798 -> 0
- patterns.yaml: 346 -> 0
- compliance.yaml: 10 -> 0
- supply-chain.yaml: 2 -> 0
- secrets.yaml: 1 -> 0
- TOTAL: 1157 -> 0

Integrity check (step 3): reviewed the 27 distinct reason classes against
the current `known_rules`/CWE-catalog landscape for a plainly-checkable
control being mislabeled out_of_scope. Flipped: 0. Reasoning: every class
name is a CATEGORICAL genericity marker, not a specific coding-defect
description a rule id could bind to -- "memory-model"/"crypto-primitive-
model"/"hardware-firmware-model"/"concurrency-scheduling-model" name
entire CWE FAMILIES requiring dataflow/runtime/hardware analysis frob's
AST-level structural checkers do not perform (a genuinely different
analysis class, not a missing rule); "advisory-design-pattern-
recommendation" (all 346 patterns.yaml entries) is, by the registry's own
design, a RECOMMENDATION entry with no negative code shape to pattern-
match, categorically distinct from an anti-pattern DEFECT entry a
detector could target; the compliance/supply-chain "process"/"advisory"
entries are explicitly tagged as organizational-process controls by their
own `checkability` field, not code properties. None of the 1157 rewritten
entries referenced, even loosely, a specific control this repo's rule
catalog (SEC/PERF/ARCH/COMPLIANCE families) already implements -- T-1020
(named in the dispatch) had already corrected the entries that DID map to
a live rule before this ticket was filed, consistent with finding zero
further misclassifications in the remaining set.

REG011's rule logic itself was NOT touched or loosened -- confirmed with
the existing `TestOutOfScopeCaughtBy::test_reason_naming_no_control_warns`
unit test (a synthetic fixture using the EXACT pre-rewrite
"advisory-design-pattern-recommendation" text with no "none --" marker)
still failing/warning exactly as before, proving the rule still rejects a
genuinely unaccountable excuse.

Evidence: the T-0678 cross-corpus registry meta-test suite (which this
change's registry-YAML edits must not break -- verifies cross_refs
mutual-navigability and the prose-only-retrofit id/count/source_doc
integrity across the whole registry) plus the existing REG011 unit tests,
all still green after the rewrite; and the full-repo
`frob check --only registry` run showing REG011 at zero.

### Changed
```
 docs/design/registry/compliance.yaml   |   20 +-
 docs/design/registry/patterns.yaml     |  692 +++++++-------
 docs/design/registry/secrets.yaml      |    2 +-
 docs/design/registry/supply-chain.yaml |    4 +-
 docs/design/registry/weaknesses.yaml   | 1596 ++++++++++++++++----------------
 tickets.md                             |  101 +-
 6 files changed, 1257 insertions(+), 1158 deletions(-)
```

### Evidence
- `tests/unit/strata/test_registry_cross_corpus_totality.py::TestCrossCorpusLinkageIntegrity::test_every_cross_ref_resolves_to_a_real_id` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_registry_cross_corpus_totality.py::TestCrossCorpusLinkageIntegrity::test_every_cross_ref_is_mutually_navigable` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_registry_cross_corpus_totality.py::TestProseOnlyRetrofitIntegrity::test_retrofit_counts_and_source_doc_pointers_hold` (pytest node id, verified passing when recorded)
- `tests/test_registry_exhaustiveness.py::TestOutOfScopeCaughtBy::test_reason_naming_no_control_warns` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 0 error(s), 1708 warning(s), 340 waived
- error-findings: none (measured, zero errors)
