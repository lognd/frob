## Done report

Verify-first finding: T-0407 (unified typed registry model) and T-0424
(check-coverage.yaml, the reflexive registry) already landed before this
ticket was filed, satisfying the ticket's own "supersedes T-0343 hand-
maintained handled_by" framing at the STRUCTURAL level -- entries already
use a typed `Disposition` model, not raw regex-matched strings. So the
delta this pass targets is specifically the piece the ticket body calls
out as still missing: a code-side `frob:enforces` directive plus the
BIDIRECTIONAL conformance gate cross-checking it against yaml's hand-typed
`handled_by`.

Built: (1) a new `EdgeKind.ENFORCES` + `frob:enforces <concept-id>`
comment-DSL verb (`frob.graph._models`, `frob.graph.dsl`) -- a rule's own
code declares which registry concept(s) it enforces, parsed by the same
five-language DSL parser every other frob: directive already uses. (2)
`registry_gate` gained an optional keyword-only `snapshot: GraphSnapshot
| None = None` parameter. When supplied, two new rules run: REG008 (an
entry dispositioned `handled_by:<rule>` with no `frob:enforces <entry-id>`
edge anywhere in code -- yaml claims enforcement the code does not
declare) and REG009 (a `frob:enforces` edge naming a concept id absent
from every loaded registry file -- a typo, or code enforcing something
the corpus never enumerated). Both WARN, not ERROR (justified in the
Done report and in the new RECONCILIATION.md#reg008reg009-t-0428 section):
this repo's ~1950 registry entries predate `frob:enforces` entirely, so
promoting to ERROR would immediately red the build for the whole existing
corpus, which is not this ticket's job to backfill in one pass -- the same
posture INV003/INV004 started in. `snapshot=None` (the default) skips
both checks entirely rather than failing every caller that has not wired
a GraphSnapshot through, so this is backward compatible with every
existing `registry_gate` call site/test.

Wired the real `frob check` invocation to pass `st.snapshot` (the same
GraphSnapshot every other code-anchor gate already loads), and added
CHK-GATE-REG008/REG009 (T-0428's own rules) + CHK-GATE-INV006 (T-0408's,
missed from check-coverage.yaml when that ticket landed) reflexive
entries to check-coverage.yaml with `frob:enforces` directives on their
own gate functions, proving the mechanism end-to-end on itself (a real,
non-vacuous self-check, not just unit-test fixtures).

NOT done in this pass (disclosed, not silently cut): the ticket's full
acceptance line ("NO hand-typed handled_by remains as the source of
truth") is NOT met -- deriving `handled_by` FROM `frob:enforces` (rather
than cross-checking the two) would mean rewriting every consumer of
`RegistryEntry.disposition` across ~1950 existing entries and retracting
the hand-typed grammar entirely, a repo-wide migration comparable in
scope to T-0407 itself and well outside this ticket's budget. What
shipped is the bidirectional CONFORMANCE gate the ticket's own "TWO-SSOT
CONFORMANCE" section demands as the precondition for that larger
migration to be sound -- the full swap to derived-only `handled_by` is
left as a distinct, larger follow-up (the check-coverage.yaml pre-
existing 82-vs-known-rules drift test failure, already broken on `main`
before this ticket, is untouched -- confirmed via `git stash` on this
same commit, not a regression this pass introduced).

### Changed
```
 CHANGELOG.md               |  18 +++++++
 docs/modules/gates.md      |  31 ++++++++++++
 pyproject.toml             |   2 +-
 src/frob/gates/__init__.py | 118 +++++++++++++++++++++++++++++++++++++++++++++
 tests/test_gates.py        |  89 ++++++++++++++++++++++++++++++++++
 tickets.md                 | 101 ++++++++++++++++++++++++++++++++++++--
 uv.lock                    |   2 +-
 7 files changed, 356 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/test_registry_exhaustiveness.py::TestEnforcesConformance::test_handled_by_with_no_frob_enforces_edge_warns` (pytest node id, verified passing when recorded)
- `tests/test_registry_exhaustiveness.py::TestEnforcesConformance::test_handled_by_with_frob_enforces_edge_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_registry_exhaustiveness.py::TestEnforcesConformance::test_no_snapshot_skips_reg008_reg009` (pytest node id, verified passing when recorded)
- `tests/test_registry_exhaustiveness.py::TestEnforcesConformance::test_phantom_enforces_edge_warns` (pytest node id, verified passing when recorded)
- `tests/test_registry_exhaustiveness.py::TestEnforcesConformance::test_matching_enforces_edge_no_reg009` (pytest node id, verified passing when recorded)
