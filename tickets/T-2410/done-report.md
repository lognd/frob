## Done report

Implemented a real, language-correct publicness rule for .strata,
replacing the unconditional public=True placeholder T-2365's behavioral
capability suite caught.

strata-core's grammar only carries a `clearance` clause (Public/
Internal/Secret) on three construct kinds -- node/store/queue
(grammar_node.rs, grammar_infra.rs's parse_store/parse_queue) -- every
other construct kind (module/flow/boundary/cache/cdn/balancer/resource/
assert/assume/refine/policy/operation/scenario) has no surface-syntax
visibility concept at all and stays public=True, honestly rather than
as a blanket placeholder.

Wiring: `_declared_clearances` (new helper, threaded alongside
`_declared_items`) maps each (keyword, id) to its own parsed entry's
`clearance` field or None when the construct kind has none.
`_locate_declared_items` takes this map and derives
`public = True if clearance is None else clearance == "Public"` per
symbol, via a new `_build_symbol` helper split out to keep the
locator's own function under ARCH001's 60-line threshold (a real
constraint hit while wiring this in, not incidental cleanup).

Then flipped `_capability_publicness_status`'s strata branch from
KNOWN_GAP to IMPLEMENTED (src/frob/lang/_support.py) and removed the
now-stale T-2410 KNOWN_GAP_TRACKING_TICKETS entry -- this is what makes
tests/test_lang_conformance_gate.py::TestBehavioralCapabilityCheck's
parametrized suite start actually exercising (strata, publicness)
against the real litmus fixture (design/litmus/chirp.strata: `node
author` declares clearance Public, several other nodes declare
clearance Internal -- a genuine mixed True/False shape, not a vacuous
pass).

Widened scope from the ticket's original single-file declaration to
also include src/frob/lang/_support.py (the registry flip is
indivisible from the walker fix -- a real rule with the registry still
claiming KNOWN_GAP would be a lie in the other direction),
docs/modules/lang.md (the capability's own doc note), and
tests/unit/test_lang_strata.py (its pre-existing
test_all_symbols_are_public locked in the OLD placeholder behavior and
had to be replaced with a test asserting the real mixed shape) -- each
widening recorded via `frob ticket scope --add --reason`.

Verification: ran the full strata/lang-conformance/lang-support test
files after `frob natives build` (strata_core/frob_core were missing in
this fresh worktree). Initial run surfaced ARCH001 on
_locate_declared_items (82 lines, threshold 60) from the added
clearance-lookup logic -- fixed by extracting _find_located_index and
_build_symbol as named helpers, re-verified with `frob check
--land-parity`: clean, 0 unscoped errors.

Filed: T-2508 -- audit non-node/store/queue strata constructs
for a future clearance concept (low-priority, disclosed non-blocking
follow-up; not required for T-2410's own scope to be complete).

### Changed
```
 docs/modules/lang.md               |  22 +++---
 src/frob/lang/_support.py          |  29 +++-----
 src/frob/lang/_walk_strata.py      | 139 ++++++++++++++++++++++++++++---------
 tests/unit/test_lang_strata.py     |  19 ++++-
 tickets/T-2410/done-report.md      |  77 ++++++++++++++++++++
 tickets/T-2410/ticket.md           |  40 ++++++++++-
 tickets/T-draft-5d681740/ticket.md |  38 ++++++++++
 7 files changed, 299 insertions(+), 65 deletions(-)
```

### Evidence
- `tests/unit/test_lang_strata.py::TestParseStrata::test_publicness_is_derived_from_clearance_not_a_blanket_true` (pytest node id, verified passing when recorded)
- `tests/test_lang_conformance_gate.py::TestBehavioralCapabilityCheck::test_implemented_capability_behaves_as_claimed[strata-publicness]` (pytest node id, verified passing when recorded)
- `tests/test_lang_conformance_gate.py::TestBehavioralCapabilityCheck::test_every_registered_language_is_covered` (pytest node id, verified passing when recorded)
- `tests/test_lang_conformance_gate.py::TestCapabilityConformanceGate::test_real_registry_is_behaviorally_clean` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PRE001@tickets/T-2410, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md
